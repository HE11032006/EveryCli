"""
Exceptions spécifiques à EveryCli.
"""

class EveryCliError(Exception):
    """Classe de base pour toutes les erreurs EveryCli."""
    pass

class DataError(EveryCliError):
    """Base pour les erreurs liées aux données (YAML)."""
    pass

class YamlFormatError(DataError):
    """Soulevée quand un fichier YAML est mal formaté."""
    def __init__(self, file_path: str, message: str):
        self.file_path = file_path
        super().__init__(f"Erreur de syntaxe dans {file_path} : {message}")

class ModelError(EveryCliError):
    """Base pour les erreurs liées au modèle d'IA."""
    pass

class ModelNotFoundError(ModelError):
    """Soulevée quand le modèle sémantique est introuvable."""
    pass

class DaemonError(EveryCliError):
    """Base pour les erreurs liées au daemon."""
    pass

class DaemonConnectionError(DaemonError):
    """Soulevée quand la connexion au daemon échoue."""
    pass

class DaemonAlreadyRunningError(DaemonError):
    """Soulevée quand on tente de lancer un daemon alors qu'un autre tourne déjà."""
    pass
