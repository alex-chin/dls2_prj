import os

from pravo_app.graph import graph
from pravo_app.run import run_graph


def main() -> None:
    state = {"query": os.getenv("PRAVO_QUERY", " Во время работ по замене крыши (в рамках капремонта) рабочие повредили мой кондиционер, установленный на фасаде. Подрядчик отказывается платить, УК ссылается на него. С кого взыскивать ущерб?")}
    mode = os.getenv("PRAVO_RUN_MODE", "debug")
    run_graph(graph, state, mode=mode)


if __name__ == "__main__":
    main()
