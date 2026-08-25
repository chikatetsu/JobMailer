from models.contract_type import ContractType
from models.experience import Experience
from models.remote_type import RemoteType


class FilterInput:
    def __init__(self,
                 remote_types: list[RemoteType] | None = None,
                 experiences: list[Experience] | None = None,
                 contract_types: list[ContractType] | None = None,
                 ignore_words: list[str] | None = None,
                 ignore_words_in_title: list[str] | None = None
    ):
        self.remote_types = self._init_remote_types(remote_types)
        self.experiences = self._init_experiences(experiences)
        self.contract_types = self._init_contract_types(contract_types)
        self.ignore_words = self._init_ignore_words(ignore_words)
        self.ignore_words_in_title = self._init_ignore_words_in_title(ignore_words_in_title)

    @staticmethod
    def _init_remote_types(remote_types: list[RemoteType] | None) -> list[RemoteType]:
        if not remote_types:
            remote_types = [remote_type for remote_type in RemoteType]
        return remote_types

    @staticmethod
    def _init_experiences(experiences: list[Experience] | None = None) -> list[Experience]:
        if not experiences:
            experiences = [experience for experience in Experience]
        return experiences

    @staticmethod
    def _init_contract_types(contract_types: list[ContractType] | None) -> list[ContractType]:
        if not contract_types:
            contract_types = [contract_type for contract_type in ContractType]
        return contract_types

    @staticmethod
    def _init_ignore_words(ignore_words: list[str] | None) -> list[str]:
        if not ignore_words:
            ignore_words = []
        return ignore_words

    @staticmethod
    def _init_ignore_words_in_title(ignore_words_in_title: list[str] | None) -> list[str]:
        if not ignore_words_in_title:
            ignore_words_in_title = []
        return ignore_words_in_title
