import os

from pravo_app.graph import graph
from pravo_app.run import run_graph


def main() -> None:
    state = {"query": os.getenv("PRAVO_QUERY", "Как обжаловать расторжение договора аренды?")}
    mode = os.getenv("PRAVO_RUN_MODE", "debug")
    run_graph(graph, state, mode=mode)


if __name__ == "__main__":
    main()
