import os
import subprocess
import sys
import textwrap
from typing import TYPE_CHECKING, Generic, List, Optional, Sequence, TypeVar
from typing_extensions import Annotated

import pytest

import strawberry

if TYPE_CHECKING:
    from tests.schema.test_lazy.type_a import TypeA  # noqa


T = TypeVar("T")

TypeAType = Annotated["TypeA", strawberry.lazy("tests.schema.test_lazy.type_a")]


def test_lazy_types_with_generic():
    @strawberry.type
    class Edge(Generic[T]):
        node: T

    @strawberry.type
    class Query:
        users: Edge[TypeAType]

    strawberry.Schema(query=Query)


def test_no_generic_type_duplication_with_lazy():
    from tests.schema.test_lazy.type_a import TypeB_abs, TypeB_rel
    from tests.schema.test_lazy.type_b import TypeB

    @strawberry.type
    class Edge(Generic[T]):
        node: T

    @strawberry.type
    class Query:
        users: Edge[TypeB]
        relatively_lazy_users: Edge[TypeB_rel]
        absolutely_lazy_users: Edge[TypeB_abs]

    schema = strawberry.Schema(query=Query)

    expected_schema = textwrap.dedent(
        """
        type Query {
          users: TypeBEdge!
          relativelyLazyUsers: TypeBEdge!
          absolutelyLazyUsers: TypeBEdge!
        }

        type TypeA {
          listOfB: [TypeB!]
          typeB: TypeB!
        }

        type TypeB {
          typeA: TypeA!
        }

        type TypeBEdge {
          node: TypeB!
        }
        """
    ).strip()

    assert str(schema) == expected_schema


@pytest.mark.parametrize(
    "commands",
    [
        pytest.param(["tests/schema/test_lazy/type_c.py"], id="script"),
        pytest.param(["-m", "tests.schema.test_lazy.type_c"], id="module"),
    ],
)
def test_lazy_types_loaded_from_same_module(commands: Sequence[str]):
    """Test if lazy types resolved from the same module produce duplication error.

    Note:
      `subprocess` is used since the test must be run as the main module / script.
    """
    result = subprocess.run(
        args=[sys.executable, *commands],
        env=os.environ,
        capture_output=True,
    )
    result.check_returncode()


def test_lazy_types_declared_within_optional():
    from tests.schema.test_lazy.type_c import Edge, TypeC

    @strawberry.type
    class Query:

        normal_edges: List[Edge[Optional[TypeC]]]
        lazy_edges: List[
            Edge[
                Optional[
                    Annotated["TypeC", strawberry.lazy("tests.schema.test_lazy.type_c")]
                ]
            ]
        ]

    schema = strawberry.Schema(query=Query)
    expected_schema = textwrap.dedent(
        """
        type Query {
          normalEdges: [TypeCOptionalEdge!]!
          lazyEdges: [TypeCOptionalEdge!]!
        }

        type TypeC {
          name: String!
        }

        type TypeCOptionalEdge {
          node: TypeC
        }
        """
    ).strip()

    assert str(schema) == expected_schema
