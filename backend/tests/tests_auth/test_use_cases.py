from src.auth.domain.models_auth import User
from src.auth.ports.user_repository import UserRepository
from src.auth.ports.password_hasher import PasswordHasher
from src.auth.ports.token_provider import TokenProvider
from src.auth.application.auth_use_cases import RegisterUser, LoginUser, LoginGuest, GUEST_SUBJECT
from src.auth.domain.exceptions import UserAlreadyExistsError
import pytest

class FakeUserRepository(UserRepository):
    """Sert à implémenter un User Repository bidon. C'est une liste de User"""
    def __init__(self,repository:list[User]):
        self.repository=repository

    def store_user(self,user:User)->None:
        self.repository.append(user)

    def get_by_mail(self, mail)->User:
        for user in self.repository:
            if user.mail==mail:
                return user


class FakePasswordHasher(PasswordHasher):
    """Sert à implémenter le port PasswordHasher de façon bidon"""

    def hash_password(self, plain_password)->str:
        return("goodpourhashpassword")

    def verify_password(self, plain_password, hashed_password)->bool:
        return True


class FakeTokenProvider(TokenProvider):
    """Classe pour implémenter le port TokenProvider de façon bidon"""

    def create_token(self, mail)->str:
        return("okpourcreate_token")

    def verify_token(self, token_used)->str:
        return("okpourverify_token")


def test_register_user_really_add():
    fake_repository=FakeUserRepository([])
    use_case=RegisterUser(repository=fake_repository,password_hasher=FakePasswordHasher())
    use_case.execute(mail="veroniquelachaux@gmail.com",plain_password="ezfhukzfu812476")
    assert len(fake_repository.repository)==1


def test_register_user_dont_add_if_mail_already_registered():
    

    with pytest.raises(UserAlreadyExistsError):
        fake_repository=FakeUserRepository([])
        use_case=RegisterUser(repository=fake_repository,password_hasher=FakePasswordHasher())
        mail_repeted="veroniquelachaux@gmail.com"
        use_case.execute(mail=mail_repeted,plain_password="ezfhukzfu812476")
        use_case.execute(mail=mail_repeted,plain_password="autrepassword")
    

def test_register_user_hash_password():
    fake_repository=FakeUserRepository([])
    use_case=RegisterUser(repository=fake_repository,password_hasher=FakePasswordHasher())
    use_case.execute(mail="veroniquelachaux@gmail.com",plain_password="thispasswordisnothashed")
    assert fake_repository.repository[0].hashed_password=="goodpourhashpassword"

def test_valid_login_creates_token():
    fake_repository=FakeUserRepository([])
    fake_hasher=FakePasswordHasher()
    fake_token_provider=FakeTokenProvider()

    register=RegisterUser(repository=fake_repository,password_hasher=fake_hasher)
    register.execute(mail="veroniquelachaux@gmail.com",plain_password="thispasswordisnothashed")

    login=LoginUser(repository=fake_repository,password_hasher=fake_hasher,token_provider=fake_token_provider)
    resultat=login.execute(mail="veroniquelachaux@gmail.com",plain_password="thispasswordisnothashed")
    assert resultat=="okpourcreate_token"


class RecordingTokenProvider(TokenProvider):
    """Token provider bidon qui mémorise l'identité pour laquelle le token est créé"""
    def __init__(self):
        self.subjects=[]

    def create_token(self, mail)->str:
        self.subjects.append(mail)
        return("token_pour_"+mail)

    def verify_token(self, token_used)->str:
        return("ok")


def test_guest_login_creates_token_for_guest_profile():
    provider=RecordingTokenProvider()
    token=LoginGuest(provider).execute()
    assert provider.subjects==[GUEST_SUBJECT]
    assert token=="token_pour_"+GUEST_SUBJECT


def test_guest_login_needs_no_user_in_repository():
    # Aucun repository n'est fourni : le profil invité ne dépend d'aucun compte
    assert LoginGuest(FakeTokenProvider()).execute()=="okpourcreate_token"
