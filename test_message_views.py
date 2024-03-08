"""Message View tests."""

# run these tests like:
#
#    FLASK_DEBUG=False python -m unittest test_message_views.py


import os
from unittest import TestCase

from models import db, Message, User

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler_test"

# Now we can import app

from app import app, CURR_USER_KEY

app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False

# This is a bit of hack, but don't use Flask DebugToolbar

app.config['DEBUG_TB_HOSTS'] = ['dont-show-debug-toolbar']

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.drop_all()
db.create_all()

# Don't have WTForms use CSRF at all, since it's a pain to test

app.config['WTF_CSRF_ENABLED'] = False


class MessageBaseViewTestCase(TestCase):
    def setUp(self):
        User.query.delete()

        u1 = User.signup("u1", "u1@email.com", "password", None)
        u2 = User.signup("u2", "u2@email.com", "password", None)

        db.session.flush()
        db.session.commit()

        m1 = Message(text="m1-text", user_id=u1.id)
        m2 = Message(text="m2-text", user_id=u2.id)
        db.session.add_all([m1,m2])
        db.session.commit()

        self.u1_id = u1.id
        self.m1_id = m1.id

        self.u2_id = u2.id
        self.m2_id = m2.id


class MessageAddViewTestCase(MessageBaseViewTestCase):
    def test_add_message(self):
        # Since we need to change the session to mimic logging in,
        # we need to use the changing-session trick:
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            # Now, that session setting is saved, so we can have
            # the rest of ours test
            resp = c.post("/messages/new", data={"text": "Hello"})

            self.assertEqual(resp.status_code, 302)

            Message.query.filter_by(text="Hello").one()

    def test_show_message(self):
        """tests if message details are shown when clickign on a message"""
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            resp = c.get(f'/messages/{self.m1_id}')
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("m1-text", html)
            self.assertIn("@u1", html)

    def test_like_message(self):
        """tests that like is properly added to message"""
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

        resp = c.post(f'/messages/{self.m2_id}/like',
               data={"location_from": "http://localhost:5000/"},
               follow_redirects = True)

        m2 = Message.query.get(self.m2_id)
        u1 = User.query.get(self.u1_id)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(m2 in u1.liked_messages, True)


    def test_unlike_message(self):
        """tests that like is properly added to message"""
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

        #To unlike, we must have a liked post
        c.post(f'/messages/{self.m2_id}/like',
               data={"location_from": "http://localhost:5000/"},
               follow_redirects = True)

        resp = c.post(f'/messages/{self.m2_id}/unlike',
               data={"location_from": "http://localhost:5000/"},
               follow_redirects = True)

        m2 = Message.query.get(self.m2_id)
        u1 = User.query.get(self.u1_id)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(m2 in u1.liked_messages, False)


    def test_delete_message(self):
        """tests that a message by the user is properly deleted"""

        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

        resp = c.post(f'/messages/{self.m1_id}/delete',
                      follow_redirects = True)


        u1 = User.query.get(self.u1_id)
        m1 = Message.query.get(self.m1_id)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(m1 in u1.messages, False)


    def test_invlaid_delete_message(self):
        """tests that a request to delete a message not by the user is
        rejected"""

        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

        resp = c.post(f'/messages/{self.m2_id}/delete',
                      follow_redirects = True)

        html = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 200)
        self.assertIn("Access unauthorized.", html)








