DEFAULT_MODEL_ID = "mistralai/Timestral-209M"
INSTALL_HINT = "pip install git+https://github.com/mistralai/timestral.git"


def timestral_available() -> bool:
    """True si le paquet `timestral` (dépôt officiel de Mistral) est installé."""
    try:
        import timestral  # noqa: F401
    except ImportError:
        return False
    return True


def load_timestral(model_id: str = DEFAULT_MODEL_ID, device: str = "cpu"):
    """Charge Timestral : d'abord depuis le cache local, puis seulement par le réseau si les poids n'y sont pas.

    Pourquoi : même avec les poids en cache, un chargement « en ligne » interroge Hugging Face avant de lire le
    cache, et cette attente réseau a coûté près de 3 minutes sur certaines connexions (6 s hors ligne). Les poids
    sont téléchargés une seule fois (cache de Hugging Face, `HF_HOME`), les chargements suivants restent locaux.

    Raises:
        ImportError: si le paquet n'est pas installé (dépendance optionnelle, absente de pyproject.toml).
    """
    try:
        from timestral import TimestralForecaster
    except ImportError as error:
        raise ImportError(f"Timestral n'est pas installé : {INSTALL_HINT}") from error
    try:
        return TimestralForecaster.from_pretrained(model_id, device=device, local_files_only=True)
    except Exception:  # poids absents du cache : premier chargement, téléchargement nécessaire
        return TimestralForecaster.from_pretrained(model_id, device=device)
