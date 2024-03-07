"""Message model tests."""

# run these tests like:
#
#    python -m unittest test_user_model.py


from app import app
import os
from unittest import TestCase
from sqlalchemy.exc import IntegrityError

from models import db, User, Message, Follow

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


class MessageModelTestCase(TestCase):
    def setUp(self):
        User.query.delete()
        Message.query.delete()

        u1 = User.signup("u1", "u1@email.com", "password", None)
        u2 = User.signup("u2", "u2@email.com", "password", None)

        db.session.commit()

        m1 = Message(text="test message", user_id=u1.id)

        db.session.add(m1)
        db.session.commit()

        self.u1_id = u1.id
        self.u2_id = u2.id
        self.m1_id = m1.id

    def tearDown(self):
        db.session.rollback()

    def test_message_model(self):
        """test Message model creates a Message instance"""
        m1 = Message.query.get(self.m1_id)

        self.assertEqual(m1.text, "test message")
        self.assertIsInstance(m1, Message)

    def test_user_relationship(self):
        """test proper User/Message models relationship setup"""
        m1 = Message.query.get(self.m1_id)
        u1 = User.query.get(self.u1_id)

        self.assertEqual(m1.user, u1)

    def test_null_message(self):
        """tests an Error if non_nullable fields are left null"""
        m2 = Message(text=None, user_id=self.u2_id)
        db.session.add(m2)

        self.assertRaises(IntegrityError, db.session.commit)
