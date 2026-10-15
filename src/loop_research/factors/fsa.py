from collections import Counter, deque

from loop_research.factors.dsl import Node


class FrequentSubtreeAvoidance:
    """Local reconstruction: count each skeleton once per candidate."""

    def __init__(self, state: dict | None = None, window: int = 200, warmup: int = 50):
        state = state or {}
        self.history = deque((set(x) for x in state.get("history", [])), maxlen=window)
        self.blocked = dict(state.get("blocked", {}))
        self.warmup = warmup

    def inspect(self, node: Node, round_number: int) -> list[str]:
        self.blocked = {k: v for k, v in self.blocked.items() if v > round_number}
        counts = Counter(s for tree in self.history for s in tree)
        if len(self.history) >= self.warmup:
            for skeleton, count in counts.items():
                if count >= 10 and count / len(self.history) > 0.15:
                    self.blocked.setdefault(skeleton, round_number + 3)
        return sorted(node.subtrees().intersection(self.blocked))

    def observe(self, node: Node) -> None:
        self.history.append(node.subtrees())

    def snapshot(self) -> dict:
        return {"history": [sorted(x) for x in self.history], "blocked": self.blocked}
