# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from pathlib import Path

import libcst as cst
from libcst import MetadataWrapper

from libcst_mypy import MypyTypeInferenceProvider


def _test_simple_class_helper(wrapper: MetadataWrapper) -> None:
    mypy_nodes = wrapper.resolve(MypyTypeInferenceProvider)
    m = wrapper.module
    assign = cst.ensure_type(
        cst.ensure_type(
            cst.ensure_type(
                cst.ensure_type(m.body[1].body, cst.IndentedBlock).body[0],
                cst.FunctionDef,
            ).body.body[0],
            cst.SimpleStatementLine,
        ).body[0],
        cst.AnnAssign,
    )
    self_number_attr = cst.ensure_type(assign.target, cst.Attribute)
    assert str(mypy_nodes[self_number_attr]) == "builtins.int"

    assert str(mypy_nodes[self_number_attr.value]) == "tests.data.simple_class.Item"
    collector_assign = cst.ensure_type(
        cst.ensure_type(m.body[3], cst.SimpleStatementLine).body[0], cst.Assign
    )
    collector = collector_assign.targets[0].target
    assert str(mypy_nodes[collector]) == "tests.data.simple_class.ItemCollector"
    items_assign = cst.ensure_type(
        cst.ensure_type(m.body[4], cst.SimpleStatementLine).body[0], cst.AnnAssign
    )
    items = items_assign.target
    assert str(mypy_nodes[items]) == "typing.Sequence[tests.data.simple_class.Item]"


def test_simple_class_types() -> None:
    source_path = Path(__file__).parent / "data" / "simple_class.py"
    file = str(source_path)
    repo_root = Path(__file__).parent.parent
    cache = MypyTypeInferenceProvider.gen_cache(repo_root, [file])
    wrapper = MetadataWrapper(
        cst.parse_module(source_path.read_text()),
        cache={MypyTypeInferenceProvider: cache[file]},
    )
    _test_simple_class_helper(wrapper)
