"""User View tests"""

from app import app, CURR_USER_KEY
import os
from unittest import TestCase

from models import db, Message, User

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler_test"

# Now we can import app


app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False

# This is a bit of hack, but don't use Flask DebugToolbar

app.config['DEBUG_TB_HOSTS'] = ['dont-show-debug-toolbar']

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.drop_all()
db.create_all()

app.config['WTF_CSRF_ENABLED'] = False


class UserViewTestCase(TestCase):
    def setUp(self):
        User.query.delete()

        u1 = User.signup("u1", "u1@email.com", "password", None)

        u2 = User.signup("u2", "u2@email.com", "password", None)

        db.session.commit()

        self.u1_id = u1.id
        self.u2_id = u2.id

    def tearDown(self):
        db.session.rollback()

    def test_user_login_success(self):
        """Tests that user gets logged in with valid credentials"""

        with app.test_client() as client:
            resp = client.post('/login',
                               data={"username": "u1",
                                     "password": "password"},
                               follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            # check the flash message is there
            self.assertIn("Hello, u1!", html)

    def test_user_login_fail(self):
        """Tests that user does not get logged if using invalid credentials"""

        with app.test_client() as client:
            # login with incorrect password
            resp = client.post('/login',
                               data={"username": "u2",
                                     "password": "hacker"},
                               follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("Invalid credentials.", html)

    def test_view_following(self):
        """Tests that user is able to see following pages for any user"""
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            u1 = User.query.get(self.u1_id)
            u2 = User.query.get(self.u2_id)

            u2.following.append(u1)

            resp = client.get(f'/users/{self.u2_id}/following')
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("@u1", html)

    def test_view_followers(self):
        """Tests that user is able to see follower page for any user"""
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            u1 = User.query.get(self.u1_id)
            u2 = User.query.get(self.u2_id)

            u2.following.append(u1)

            resp = client.get(f'/users/{self.u1_id}/followers')
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("@u2", html)

    def test_logged_out_view(self):
        """Tests that logged out users are blocked from viewing user's
        following page"""
        with app.test_client() as client:

            resp = client.get(
                f'/users/{self.u1_id}/followers',
                follow_redirects=True
            )

            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("Access unauthorized.", html)


    def test_follow_user(self):
        """Tests that user correctly can follow another user"""

        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            u1 = User.query.get(self.u1_id)
            u2 = User.query.get(self.u2_id)


            resp = client.post(f'/users/follow/{self.u2_id}',
                               follow_redirects=True)

            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertEqual(u2.is_followed_by(u1), True)
            self.assertIn(f"""<li class="stat">
            <p class="small">Following</p>
            <h4>
              <a href="/users/{self.u1_id}/following">
                1
              </a>
            </h4>
          </li>""", html)


    def test_unfollow_user(self):
        """Tests that user correctly can unfollow another user"""

        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            u1 = User.query.get(self.u1_id)
            u2 = User.query.get(self.u2_id)

            #u1 is now following u2
            u1.following.append(u2)

            resp = client.post(f'/users/stop-following/{self.u2_id}',
                               follow_redirects=True)

            html = resp.get_data(as_text=True)
            # string_html = str(html)

            self.assertEqual(resp.status_code, 200)
            self.assertEqual(u2.is_followed_by(u1), False)

            self.assertIn(f"""<li class="stat">
            <p class="small">Following</p>
            <h4>
              <a href="/users/{self.u1_id}/following">
                0
              </a>
            </h4>
          </li>""", html)

    def test_delete_user(self):
        """test if logged in user can delete their profile and logged out"""

        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

        resp = client.post(f"/users/delete", follow_redirects=True)

        html = resp.get_data(as_text=True)

        self.assertIn('User has been deleted, goodbye!', html)
        #querying for a deleted user should give back None
        self.assertEqual(User.query.get(self.u1_id), None)

    def test_update_profile(self):
        """tests to see if the user can change their profile using valid
        form inputs"""
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

        resp = client.post('/users/profile',
                           data={"username": "newName",
                                 "email" : "new@email.com",
                                 "bio" : "this is the new me.",
                                 "password": "password"},
                                 follow_redirects=True
                                 )

        html = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 200)
        self.assertIn("@newName", html)
        self.assertIn("this is the new me", html)


    def test_invalid_user_update(self):
        """Tests to see if a user tries to update their profile with an existing
        username will get a form warning message"""
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

        resp = client.post('/users/profile',
                           data={"username": "u2",
                                 "email" : "u1@email.com",
                                 "password": "password"},
                                 follow_redirects=True
                                 )

        html = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 200)
        self.assertIn("Username already exists.", html)