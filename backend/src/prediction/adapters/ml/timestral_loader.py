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
    """Charge Timestral (poids téléchargés depuis Hugging Face au premier appel, en cache ensuite).

    Raises:
        ImportError: si le paquet n'est pas installé (dépendance optionnelle, absente de pyproject.toml).
    """
    try:
        from timestral import TimestralForecaster
    except ImportError as error:
        raise ImportError(f"Timestral n'est pas installé : {INSTALL_HINT}") from error
    return TimestralForecaster.from_pretrained(model_id, device=device)
