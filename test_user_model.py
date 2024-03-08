"""User model tests."""

# run these tests like:
#
#    python -m unittest test_user_model.py


import os
from unittest import TestCase
from sqlalchemy.exc import IntegrityError

from models import db, User

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler_test"

# Now we can import app


# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.drop_all()
db.create_all()


class UserModelTestCase(TestCase):
    def setUp(self):
        User.query.delete()

        u1 = User.signup("u1", "u1@email.com", "password", None)
        u2 = User.signup("u2", "u2@email.com", "password", None)

        db.session.commit()
        self.u1_id = u1.id
        self.u2_id = u2.id

    def tearDown(self):
        db.session.rollback()

    def test_user_model(self):
        """tests User instance is made properly"""
        u1 = User.query.get(self.u1_id)

        # User should have no messages & no followers
        self.assertEqual(len(u1.messages), 0)
        self.assertEqual(len(u1.followers), 0)

        # User should have the right username
        self.assertEqual(u1.username, "u1")

    def test_is_following(self):
        """tests that is_following method evaluates following relationship correctly
        if user is following the other"""

        u1 = User.query.get(self.u1_id)
        u2 = User.query.get(self.u2_id)

        u1.following.append(u2)

        self.assertEqual(u1.is_following(u2), True)
        self.assertEqual(u2.is_following(u1), False)

    def test_is_not_following(self):
        """tests that is_following method evaluates following relationship correctly
        if user is not following the other"""

        u1 = User.query.get(self.u1_id)
        u2 = User.query.get(self.u2_id)

        u2.following.append(u1)

        self.assertEqual(u1.is_following(u2), False)
        self.assertEqual(u2.is_following(u1), True)

    def test_is_followed_by(self):
        """tests that is_followed_by method evaluates true
        if user follows other user"""

        u1 = User.query.get(self.u1_id)
        u2 = User.query.get(self.u2_id)

        u2.following.append(u1)

        self.assertEqual(u1.is_followed_by(u2), True)
        self.assertEqual(u2.is_followed_by(u1), False)

    def test_is_not_followed_by(self):
        """tests that is_followed_by method returns false if user doesn't follow
        other user"""

        u1 = User.query.get(self.u1_id)
        u2 = User.query.get(self.u2_id)

        self.assertEqual(u1.is_followed_by(u2), False)

    def test_valid_user_signup(self):
        """tests proper user sign up if given valid credentials"""

        u3 = User.signup("u3", "u3@email.com", "password", None)

        self.assertIsInstance(u3, User)
        self.assertEqual(u3.email, "u3@email.com")

    def test_invalid_user_signup(self):
        """tests proper error raised if user signup is given invalid credentials"""

        # u2 already exists
        User.signup("u2", "u2@email.com", "password", None)
        User.signup(None, "None", "password", None)

        self.assertRaises(IntegrityError, db.session.commit)

    def test_valid_user_authenticate(self):
        """tests that authenticate method returns correct user instance if
        user passes valid credentials"""

        u1_auth_check = User.authenticate("u1", "password")
        u1 = User.query.get(self.u1_id)

        self.assertEqual(u1_auth_check, u1)

    def test_invalid_user_authenticate(self):
        """tests that authenticate method returns false if
        invalid credentials are passed"""

        invalid_username = User.authenticate("not_u1", "password")
        invalid_password = User.authenticate("u1", "wrongpassword")

        self.assertEqual(invalid_username, False)
        self.assertEqual(invalid_password, False)

    # TODO: try to use assertFalse & asserTrue
