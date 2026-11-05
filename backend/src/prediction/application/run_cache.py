"""Sauvegarde des exécutions du benchmark : une interruption ne fait plus perdre des heures de calcul.

Chaque exécution terminée (modèle, graine, année de test) est écrite dans un fichier. Au relancement,
les exécutions déjà faites sont relues au lieu d'être refaites. La clé de configuration change dès que le
code des modèles ou les réglages changent : un ancien résultat ne peut donc pas être réutilisé par erreur.
"""
import hashlib
import pickle
from pathlib import Path

from src.prediction.application.benchmark import RunResult


def source_fingerprint(*roots: str) -> str:
    """Empreinte du contenu de tous les fichiers .py des dossiers donnés."""
    digest = hashlib.sha256()
    for root in roots:
        for file in sorted(Path(root).rglob("*.py")):
            digest.update(str(file).encode())
            digest.update(file.read_bytes())
    return digest.hexdigest()


def config_key(**settings) -> str:
    """Clé courte et stable à partir de réglages (nombres, textes, empreintes)."""
    text = "|".join(f"{k}={settings[k]}" for k in sorted(settings))
    return hashlib.sha256(text.encode()).hexdigest()[:16]


class RunCache:
    def __init__(self, directory: str, key: str):
        self.directory = Path(directory) / key
        self.directory.mkdir(parents=True, exist_ok=True)

    def _file(self, model: str, seed: int | None, test_year: int | None) -> Path:
        return self.directory / f"{model}__{seed}__{test_year}.pkl"

    def get(self, model: str, seed: int | None, test_year: int | None) -> RunResult | None:
        file = self._file(model, seed, test_year)
        if not file.is_file():
            return None
        try:
            with file.open("rb") as handle:
                return pickle.load(handle)
        except Exception:                                  # fichier tronqué par une interruption : on refait
            return None

    def put(self, result: RunResult, seed: int | None) -> None:
        file = self._file(result.model, seed, result.test_year)
        temporary = file.with_suffix(".tmp")
        with temporary.open("wb") as handle:
            pickle.dump(result, handle)
        temporary.replace(file)                            # écriture atomique : jamais de fichier à moitié écrit
