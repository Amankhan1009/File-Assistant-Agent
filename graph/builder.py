from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from graph.nodes import agent_node
from graph.routing import route_after_agent
from graph.state import AgentState
from graph.tool_observability import create_observable_tool_node


def build_graph(
    checkpointer: BaseCheckpointSaver | None = None,
):
    """
    Build and compile the File Assistant's tool-calling agent graph.

    Execution flow:

        START
          ↓
        agent
          ↓
        route_after_agent
          ├── tools → tools → agent
          └── end   → END

    The optional checkpointer enables persistent graph state.

    Tool execution observability is implemented through ToolNode's native
    tool-call wrapper without changing the graph architecture.
    """
    builder = StateGraph(
        AgentState,
    )

    tool_node = (
        create_observable_tool_node()
    )

    builder.add_node(
        "agent",
        agent_node,
    )

    builder.add_node(
        "tools",
        tool_node,
    )

    builder.add_edge(
        START,
        "agent",
    )

    builder.add_conditional_edges(
        "agent",
        route_after_agent,
        {
            "tools": "tools",
            "__end__": END,
        },
    )

    builder.add_edge(
        "tools",
        "agent",
    )

    return builder.compile(
        checkpointer=checkpointer,
    )