"""Regression checks for incomplete native source recovery diagnostics."""
import importlib.util
from pathlib import Path
import unittest
from types import SimpleNamespace
from collections import defaultdict
from unittest.mock import patch


ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location(
    'nuitka_decompiler', ROOT / 'nuitka_decompiler.py')
DECOMPILER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DECOMPILER)


class SourceAuditTests(unittest.TestCase):
    def test_docstring_only_body_is_reported_as_potential_loss(self):
        source = 'def recover(value):\n    """Recovered documentation."""\n'
        code_objects = [{'qualname': 'recover', 'varnames': ['value', 'result']}]
        audit = DECOMPILER._ndx_audit_source(source, code_objects)
        self.assertEqual(audit['status'], 'partial')
        self.assertTrue(any(issue['kind'] == 'dropped_body' and
                            issue['name'] == 'recover'
                            for issue in audit['issues']))

    def test_function_with_a_return_is_not_a_dropped_body(self):
        audit = DECOMPILER._ndx_audit_source('def recover(value):\n    return value\n')
        self.assertFalse(any(issue['kind'] == 'dropped_body'
                             for issue in audit['issues']))

    def test_unqualified_native_method_name_matches_qualified_ast_definition(self):
        source = 'class Window:\n    def refresh(self):\n        return 1\n'
        code_objects = [{'qualname': 'refresh', 'varnames': ['self']}]
        audit = DECOMPILER._ndx_audit_source(source, code_objects)
        self.assertEqual(audit['missing_functions'], [])
        self.assertFalse(any(issue['kind'] == 'missing_definition'
                             for issue in audit['issues']))

    def test_class_body_argcount_is_not_constructor_signature(self):
        source = ('class Dialog:\n    pass\n\n'
                  'def show(manager, parent):\n    return Dialog(manager, parent)\n')
        code_objects = [
            {'qualname': 'Dialog', 'argcount': 0, 'kwonlyargcount': 0, 'flags': 0},
            {'qualname': 'show', 'argcount': 2, 'kwonlyargcount': 0, 'flags': 0},
        ]
        audit = DECOMPILER._ndx_audit_source(source, code_objects)
        self.assertFalse(any(issue['kind'] == 'dropped_body'
                             for issue in audit['issues']))


class NativeSemanticsTests(unittest.TestCase):
    def renderer(self):
        state = SimpleNamespace(L=SimpleNamespace(freevars=(), co=None, var_of_sym={}),
                                img=SimpleNamespace(fmt='pe'), blocks={}, sym_names={},
                                sym_keys={}, var_names={}, semantic_names=set(), temp_inline={})
        state._nested_statement_lists = DECOMPILER.Structurer._nested_statement_lists
        renderer = DECOMPILER.NdxRenderer(state, ['value'], 1)
        renderer._mark_comp_targets = lambda statements: setattr(renderer, '_comp_targets', set())
        return renderer

    def test_negated_comparison_preserves_python_operator(self):
        d = DECOMPILER
        comparison = d.ndx_k('cmp', 'eq', d.ndx_k('par', 0), d.ndx_k('const', 1))
        negative = object.__new__(d.Structurer)._negate_cond(comparison)
        self.assertEqual(negative.op, 'not')
        self.assertIs(negative.a, comparison)
        expression = self.renderer()._negated_condition_text(comparison, 'value == 1')
        events = []
        class Value:
            def __eq__(self, other):
                events.append('eq')
                return True
            def __ne__(self, other):
                events.append('ne')
                return True
        self.assertFalse(eval(expression, {'value': Value()}))
        self.assertEqual(events, ['eq'])

    def test_fresh_dict_stores_are_not_moved_across_effects(self):
        d = DECOMPILER
        renderer = self.renderer()
        allocation = d.ndx_k('dict_empty', n=100)
        for value, line in [(d.ndx_k('call', 'work', []), None),
                            (d.ndx_k('var', 'payload'), None),
                            (d.ndx_k('par', 0), 11)]:
            allocation.op = 'dict_empty'
            statements = [d.NdxSt('assign', a='payload', b=allocation, line=10),
                          d.NdxSt('store_sub', a=allocation, b=d.ndx_k('const', 'key'),
                                  c=value, line=line)]
            renderer._rebuild_fresh_dicts(statements)
            self.assertEqual(len(statements), 2)
            self.assertEqual(allocation.op, 'dict_empty')

    def test_heap_local_keeps_captured_cell(self):
        d = DECOMPILER
        lifter = object.__new__(d.BodyLifter2)
        lifter.img = SimpleNamespace(fmt='pe')
        lifter.abi = d.abi_for('pe', (3, 11))
        regs = {'rbx': d.ndx_k('func_locals')}
        lifter._reg = lambda name: regs.get(name)
        lifter._setreg = lambda name, value: regs.__setitem__(name, value)
        lifter.argcount, lifter.varnames = 1, ['arg', 'first', 'captured']
        lifter.var_of_sym, lifter.authoritative_loc_names = {}, {}
        lifter.captured_cell_names, lifter.captured_cell_indices, lifter.captured_values = {}, {}, {}
        lifter._cur_block = SimpleNamespace(start=1, end=50, ops=[])
        lifter.store_sites = []
        cell = d.ndx_k('cell_new', n=10)
        lifter._note_slot_store('rbx', 8, cell, SimpleNamespace(address=20))
        lifter._load_mem('rax', 'rbx', 8, SimpleNamespace(address=21))
        self.assertIs(regs['rax'], cell)
        regs['rcx'] = cell
        lifter.gen_mode, lifter.slot_syms = True, {}
        lifter.symbol_locations = defaultdict(set)
        lifter._svkey_of = d.sv_key
        lifter._record_aggregate_field = lambda *args: None
        value = d.ndx_k('list_empty', n=22)
        lifter._store_slot('rcx', 0x10, value)
        self.assertEqual(lifter._cur_block.ops[-1].kind, 'closure_store')

    def test_with_fold_preserves_user_exception_handler(self):
        d = DECOMPILER
        renderer = self.renderer()
        owner = d.ndx_k('var', 'ctx')
        enter = d.NdxSt('assign', a='entered', b=d.ndx_k(
            'mcall', owner, d.ndx_k('const', '__enter__'), []))
        handler = d.NdxSt('expr', a=d.ndx_k('call', 'user_effect', []))
        protected = d.NdxSt('try', a=[d.NdxSt('expr', a=d.ndx_k('call', 'work', []))],
                            b=[(BaseException, [handler], None, None)], c=[])
        exit_call = d.NdxSt('expr', a=d.ndx_k('mcall', owner, d.ndx_k('const', '__exit__'),
                                               [d.ndx_k('none') for _ in range(3)]))
        result = renderer._fold_ir_with_and_shortcircuit([enter, protected, exit_call])
        self.assertFalse(any(statement.kind == 'with_block' for statement in result))
        self.assertIs(result[1], protected)

    def test_temporary_call_keeps_order_before_callable_lookup(self):
        d = DECOMPILER
        renderer = self.renderer()
        statements = [d.NdxSt('assign', a='_v1', b=d.ndx_k(
            'call', d.ndx_k('global', 'compute'), [], n=10)),
            d.NdxSt('return', a=d.ndx_k('call', d.ndx_k(
                'call', d.ndx_k('global', 'choose'), [], n=20),
                [d.ndx_k('var', '_v1')], n=30))]
        source = 'def recovered(value):\n' + '\n'.join('    ' + line
                                                        for line in renderer.render(statements))
        events = []
        def compute():
            events.append('compute')
            return 7
        def choose():
            events.append('choose')
            return lambda value: value
        namespace = {'compute': compute, 'choose': choose}
        exec(source, namespace)
        self.assertEqual(namespace['recovered'](0), 7)
        self.assertEqual(events, ['compute', 'choose'])

    def test_formatting_happens_before_intervening_call(self):
        d = DECOMPILER
        renderer = self.renderer()
        statements = [d.NdxSt('assign', a='_ndx_value_1', b=d.ndx_k(
            'format', d.ndx_k('par', 0), d.ndx_k('const', ''), n=3)),
            d.NdxSt('expr', a=d.ndx_k('call', 'touch', [], n=4)),
            d.NdxSt('assign', a='message', b=d.ndx_k(
                'fstring', [d.ndx_k('var', '_ndx_value_1')], n=5))]
        source = 'def recovered(value):\n' + '\n'.join('    ' + line
                                                        for line in renderer.render(statements))
        events = []
        class Value:
            def __format__(self, spec):
                events.append('format')
                return 'V'
        namespace = {'touch': lambda: events.append('touch')}
        exec(source, namespace)
        namespace['recovered'](Value())
        self.assertEqual(events, ['format', 'touch'])

    def test_empty_loop_is_not_discarded(self):
        d = DECOMPILER
        loop = d.NdxSt('while', a=d.ndx_k('call', 'predicate', []),
                       b=[d.NdxSt('pass')])
        self.assertEqual(self.renderer()._drop_empty_loops([loop]), [loop])

    def test_inplace_helper_follows_proven_guarded_tail_dispatch(self):
        d = DECOMPILER
        def ins(address, mnemonic, operands):
            return SimpleNamespace(address=address, mnemonic=mnemonic, op_str=operands)
        compact = [ins(0x100, 'mov', 'rbx, rcx'),
                   ins(0x103, 'mov', 'rcx, qword ptr [rcx]'),
                   ins(0x106, 'cmp', 'qword ptr [rcx + 8], rax'),
                   ins(0x10a, 'jne', '0x120'),
                   ins(0x10c, 'mov', 'qword ptr [rbx], rax'),
                   ins(0x120, 'mov', 'rcx, rbx'),
                   ins(0x123, 'add', 'rsp, 0x20'),
                   ins(0x127, 'pop', 'rbx'), ins(0x128, 'jmp', '0x200')]
        generic = [ins(0x200, 'mov', 'rbx, rcx'),
                   ins(0x203, 'mov', 'rcx, qword ptr [rcx]'),
                   ins(0x206, 'mov', 'rax, qword ptr [rcx + 8]'),
                   ins(0x20a, 'mov', 'qword ptr [rbx], rax')]
        resolver = object.__new__(d.HelperResolver)
        resolver.img = SimpleNamespace(fmt='pe')
        resolver._func_insns = lambda va: {0x100: compact, 0x200: generic}.get(va, [])
        resolver._native_classifier = SimpleNamespace(
            _binop_slot=lambda va: ('+', None) if va == 0x200 else None,
            _str_concat_helper=lambda va: None)
        with patch.object(d, 'detect_python_version', return_value=(3, 10)):
            self.assertEqual(resolver._native_inplace_binop_name(0x100),
                             'INPLACE_OPERATION_ADD')
            compact.insert(3, ins(0x108, 'mov', 'rdx, rax'))
            self.assertIsNone(resolver._native_inplace_binop_name(0x100))

    def test_loop_exit_uses_loop_iterator_not_unpack_iterator(self):
        d = DECOMPILER
        loop_iter = d.ndx_k('iter', d.ndx_k('var', 'items'), n=100)
        unpack_iter = d.ndx_k('iter', d.ndx_k('var', 'item'), n=200)
        def block(start, iterator=None, edges=()):
            ops = [d.NdxOp('calc', a=d.ndx_k('next', iterator), va=start)] if iterator else []
            return SimpleNamespace(start=start, edges=list(edges), ops=ops,
                                   kind='normal', conds=[], succs=[])
        state = object.__new__(d.Structurer)
        state.loops = {1: {'body': {1, 2, 3}}}
        state.blocks = {1: block(1), 2: block(2, loop_iter, [(10, 'stopiter')]),
                        3: block(3, unpack_iter, [(20, 'stopiter')]),
                        10: block(10), 20: block(20)}
        state.nsucc = {1: [], 2: [], 3: []}
        state._detect_for = lambda *args: ('item', d.ndx_k('var', 'items'), loop_iter)
        state._iterator_null_exception_exit = lambda target: target
        state._line_of = lambda block: None
        state._seq_body = lambda *args, **kwargs: [d.NdxSt('pass', blocks={2})]
        state._clean_for_body = lambda statements: statements
        state.L = SimpleNamespace(gen_mode=False)
        result, after = state._structure_loop(1, set(), 0)
        self.assertEqual(after, 10)
        self.assertEqual(result[0].kind, 'for')

    def test_boxed_length_pointer_check_does_not_test_length_zero(self):
        d = DECOMPILER
        lifter = object.__new__(d.BodyLifter2)
        lifter.abi = d.abi_for('pe', (3, 10))
        lifter.co = SimpleNamespace(flags=0)
        length = d.ndx_k('len', d.ndx_k('par', 0))
        registers = {'rcx': length}
        lifter._reg = lambda name: registers.get(name)
        lifter._cur_block = SimpleNamespace(insns=[])
        boxed = lifter._semantic_call('PyLong_FromSsize_t', ('box_ssize', 1),
                                     [length], SimpleNamespace(address=10, op_str=''))
        self.assertIsNot(boxed, length)
        registers['rbx'] = boxed
        check = SimpleNamespace(address=20, mnemonic='test', op_str='rbx, rbx')
        jump = SimpleNamespace(address=22, mnemonic='jne', op_str='0x30', size=2)
        lifter._cur_block.insns = [check, jump]
        lifter._inline_length_positive_before = lambda *args: None
        lifter._generator_cbool_guard = lambda *args: None
        lifter._target_starts_exception_path = lambda target: False
        lifter._exec_test(check)
        self.assertEqual(lifter._cond_kind, 'null_or_bool')

    def test_inplace_helper_returns_native_success_not_result_truth(self):
        d = DECOMPILER
        lifter = object.__new__(d.BodyLifter2)
        lifter._cur_block = SimpleNamespace(ops=[])
        lifter.mca = None
        lifter.slot_syms = {('rbp', -8): d.ndx_k('var', 'counter')}
        lifter.authoritative_loc_names = {}
        lifter.symbol_locations = {}
        lifter._store_slot = lambda base, off, value: lifter.slot_syms.__setitem__((base, off), value)
        lifter.is_module_code = False
        pointer = d.ndx_k('stackaddr', 'rbp', -8)
        result = lifter._semantic_call('INPLACE_OPERATION_ADD', ('binop', 2),
                                       [pointer, d.ndx_k('const', 1)],
                                       SimpleNamespace(address=20, op_str=''))
        self.assertEqual((result.op, result.a), ('native_status', 'inplace_success'))
        self.assertEqual(lifter._cur_block.ops[-1].kind, 'store')
        self.assertEqual(lifter._cur_block.ops[-1].b.op, 'binop')

    def test_source_local_assignment_survives_nested_suite_rendering(self):
        d = DECOMPILER
        renderer = self.renderer()
        renderer.varnames = ['value', 'counter']
        statement = d.NdxSt('assign', a='counter', b=d.ndx_k('binop', '+',
                               d.ndx_k('var', 'counter'), d.ndx_k('const', 1)))
        self.assertEqual(renderer._drop_dead_call_assigns([statement]), [statement])

    def test_inplace_update_survives_loop_body_cleanup(self):
        d = DECOMPILER
        state = object.__new__(d.Structurer)
        state.var_names = {}
        statement = d.NdxSt('assign', a='_v2', b=d.ndx_k(
            'binop', '+', d.ndx_k('loc', ('mem', 'rbp', -8)),
            d.ndx_k('const', 1), n='inplace'))
        self.assertEqual(state._clean_for_body([statement]), [statement])

    def test_recovers_proven_inplace_slot_constant_initializer(self):
        d = DECOMPILER
        ins = lambda address, mnemonic, op_str: SimpleNamespace(
            address=address, mnemonic=mnemonic, op_str=op_str)
        location = ('mem', 'rbp', -8)
        update = d.ndx_k('binop', '+', d.ndx_k('loc', location), d.ndx_k('const', 1), n='inplace')
        block = SimpleNamespace(insns=[ins(10, 'mov', 'rdx, qword ptr [rip + 0x20]'),
                                       ins(11, 'mov', 'qword ptr [rbp - 8], rdx')],
                                ops=[d.NdxOp('store', a=location, b=update, va=20)])
        lifter = SimpleNamespace(blocks={10: block},
                                 mca=SimpleNamespace(const_for_slot=lambda va: (0, ('glob', 1))),
                                 _instruction_writes_register=lambda *args: False)
        with patch.object(d, 'rip_target', return_value=123):
            d._ndx_recover_inplace_constant_initializers(lifter)
        self.assertEqual([op.va for op in block.ops], [11, 20])
        self.assertEqual((block.ops[0].a, block.ops[0].b.a), (location, 0))
        block.ops = [d.NdxOp('store', a=location, b=update, va=20)]
        lifter.mca.const_for_slot = lambda va: (None, None)
        with patch.object(d, 'rip_target', return_value=123):
            d._ndx_recover_inplace_constant_initializers(lifter)
        self.assertEqual([op.va for op in block.ops], [20])

    def test_inline_dict_lookup_requires_proven_default_and_join(self):
        d = DECOMPILER
        def ins(address, mnemonic, op_str):
            return SimpleNamespace(address=address, mnemonic=mnemonic, op_str=op_str)
        lifter = object.__new__(d.BodyLifter2)
        lifter.img = SimpleNamespace(fmt='pe')
        lifter.py_version = (3, 10)
        lifter.abi = d.abi_for('pe', (3, 10))
        owner = d.ndx_k('const', {'a': 1})
        key, default = d.ndx_k('par', 0), d.ndx_k('const', 'missing')
        regs = {'r14': owner, 'rcx': owner, 'rdx': key, 'r8': None,
                'r9': d.ndx_k('stackaddr', 'rbp', 7), 'r15': default}
        lifter._reg = lambda reg: regs.get(reg)
        call = ins(2, 'call', 'qword ptr [rax + 0x10]')
        lifter.insns = [ins(1, 'mov', 'rax, qword ptr [r14 + 0x20]'), call,
                        ins(3, 'mov', 'rbx, qword ptr [rbp + 7]'),
                        ins(4, 'test', 'rbx, rbx'), ins(5, 'je', '0x20'),
                        ins(6, 'nop', ''), ins(7, 'nop', ''),
                        ins(0x20, 'inc', 'qword ptr [r15]'),
                        ins(0x21, 'mov', 'rbx, r15'), ins(0x22, 'jmp', '0x7')]
        proof = lifter._prove_inline_dict_get_310(call)
        self.assertIsNotNone(proof)
        value, output, fallback, end = proof
        self.assertEqual((value.op, value.b.a, output, fallback), ('mcall', 'get', ('rbp', 7), 0x21))
        self.assertEqual(end, 5)
        self.assertIs(value.a, owner)
        self.assertEqual(value.c, [key, default])
        lifter.insns[5] = ins(6, 'call', '0x99')
        self.assertIsNone(lifter._prove_inline_dict_get_310(call))
        lifter.insns[5] = ins(6, 'nop', '')
        regs['r14'] = d.ndx_k('const', {'a': 1})
        self.assertIsNone(lifter._prove_inline_dict_get_310(call))
        regs['r14'] = owner
        regs['r15'] = None
        self.assertIsNone(lifter._prove_inline_dict_get_310(call))
        regs['r15'] = default
        regs['rdi'] = d.ndx_k('tstate')
        lifter.insns = [ins(0, 'lea', 'r10, [rdi + 0x58]'),
                        ins(1, 'mov', 'qword ptr [rbp + 0x7f], r10'),
                        ins(2, 'mov', 'rax, qword ptr [r14 + 0x20]')]
        call = ins(3, 'call', 'qword ptr [rax + 0x10]')
        lifter.insns += [call, ins(4, 'mov', 'rbx, qword ptr [rbp + 7]'),
                         ins(5, 'test', 'rbx, rbx'), ins(6, 'je', '0x20'),
                         ins(7, 'nop', ''), ins(8, 'nop', ''),
                         ins(0x20, 'mov', 'r12, qword ptr [rbp + 0x7f]'),
                         ins(0x21, 'cmp', 'qword ptr [r12], 0'),
                         ins(0x22, 'jne', '0x8'),
                         ins(0x23, 'inc', 'qword ptr [r15]'),
                         ins(0x24, 'mov', 'rbx, r15'), ins(0x25, 'jmp', '0x8')]
        self.assertIsNotNone(lifter._prove_inline_dict_get_310(call))
        regs['rdi'] = d.ndx_k('par', 0)
        self.assertIsNone(lifter._prove_inline_dict_get_310(call))


class LegacySemanticSafetyTests(unittest.TestCase):
    def test_repeated_construction_is_not_duplicate_evidence(self):
        source = '''def build(self):
    self.widget = Factory()
    step(1)
    step(2)
    step(3)
    step(4)
    step(5)
    step(6)
    step(7)
    step(8)
    step(9)
    step(10)
    self.widget = Factory()
'''
        self.assertEqual(
            DECOMPILER._ndl_dedupe_repeated_stmt_blocks_v33(source), source)

    def test_conditional_body_and_unconditional_suffix_both_survive(self):
        source = '''def run(items):
    if items:
        record(1)
        record(2)
        record(3)
    record(1)
    record(2)
    record(3)
'''
        self.assertEqual(
            DECOMPILER._ndl_dedupe_compound_body_repeat_v90(source), source)

    def test_callable_arguments_are_not_packed_statement_evidence(self):
        source = 'def register():\n    subscribe(resize, setup_ui)\n'
        self.assertEqual(
            DECOMPILER._ndl_demote_sibling_method_pack_calls_v33(source), source)

    def test_module_objects_remain_valid_call_arguments(self):
        source = 'def register():\n    inspect(sys)\n'
        self.assertEqual(
            DECOMPILER._ndl_demote_module_arg_calls_v90(source), source)

    def test_absolute_memory_operand_has_no_base_register(self):
        # ``mov rax, [0x140001000]`` has no base register; the register
        # canonicaliser must return None instead of raising on it.
        base, _disp, index, _scale = DECOMPILER.parse_mem('[0x140001000]')
        self.assertIsNone(base)
        self.assertIsNone(index)
        self.assertIsNone(DECOMPILER._canon_reg(base))

    def test_register_canonicaliser_keeps_named_registers(self):
        self.assertEqual(DECOMPILER._canon_reg('esi'), 'rsi')
        self.assertEqual(DECOMPILER._canon_reg('r8d'), 'r8')


if __name__ == '__main__':
    unittest.main()
