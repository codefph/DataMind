import hashlib
import re
from collections import Counter

EMBED_DIM = 384
SPARSE_MOD = 0xFFFFFFFF


class LocalHashEmbedder:
    """本地确定性嵌入，用于在接入真实 Embedding 模型前打通检索链路。

    稠密向量：字符/词级 feature hashing；稀疏向量：词频（近似 BM25）。
    Phase 3 接入模型网关后，替换为真实 Embedding。
    """

    dim = EMBED_DIM

    @staticmethod
    def _tokens(text: str) -> list[str]:
        lowered = text.lower()
        words = re.findall(r"[a-z0-9_]+", lowered)
        cjk = re.findall(r"[\u4e00-\u9fff]", lowered)
        bigrams = [cjk[i] + cjk[i + 1] for i in range(len(cjk) - 1)]
        tokens = words + cjk + bigrams
        return tokens or ["<empty>"]

    def embed(self, text: str) -> tuple[list[float], dict[int, float]]:
        tokens = self._tokens(text)

        dense = [0.0] * self.dim
        for token in tokens:
            h = int(hashlib.sha1(token.encode("utf-8")).hexdigest(), 16)
            idx = h % self.dim
            sign = 1.0 if (h >> 3) & 1 else -1.0
            dense[idx] += sign
        norm = sum(v * v for v in dense) ** 0.5
        if norm > 0:
            dense = [v / norm for v in dense]

        sparse: dict[int, float] = {}
        for token, count in Counter(tokens).items():
            idx = int(hashlib.sha1(token.encode("utf-8")).hexdigest(), 16) % SPARSE_MOD
            sparse[idx] = sparse.get(idx, 0.0) + float(count)

        return dense, sparse

