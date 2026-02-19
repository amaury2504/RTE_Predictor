from src.auth.domain.models_auth import User
import pytest

def test_user_mail_valide():
    result=User(mail="jeanluc@gmail.com",hashed_password="YG3E7gugye")
    assert result.mail=="jeanluc@gmail.com"

def test_user_password_valide():
    result=User(mail="jeanluc@gmail.com",hashed_password="YG3E7gugye")
    assert result.hashed_password=="YG3E7gugye"

def test_user_mail_wrong_type():
    with pytest.raises(TypeError):
        User(mail=123,hashed_password="YG3E7gugye")


@pytest.mark.parametrize("valeur_mail, erreur_attendue",[
    ("",ValueError),
    (" ",ValueError),
    ("jeanlucgmail.com",ValueError),
    ("jeanluc@gmailcom",ValueError),
    (123,TypeError)])
def test_user_mail_wrong(valeur_mail,erreur_attendue):
    with pytest.raises(erreur_attendue):
        User(mail=valeur_mail,hashed_password="YG3E7gugye")

@pytest.mark.parametrize("valeur_hashed_password, erreur_attendue",[
    ("",ValueError),
    (" ",ValueError),
    (123,TypeError)])
def test_user_password_wrong(valeur_hashed_password,erreur_attendue):
    with pytest.raises(erreur_attendue):
        User(mail="jeanluc@gmail.com",hashed_password=valeur_hashed_password)
