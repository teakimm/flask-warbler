"""User View tests"""

from app import app, CURR_USER_KEY
import os
from unittest import TestCase

from models import db, User, Message

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

        db.session.flush()
        db.session.commit()

        m1 = Message(text="m1-text", user_id=u1.id)
        m2 = Message(text="m2-text", user_id=u2.id)
        db.session.add_all([m1, m2])
        db.session.commit()

        self.u1_id = u1.id
        self.m1_id = m1.id

        self.u2_id = u2.id
        self.m2_id = m2.id

    def tearDown(self):
        db.session.rollback()

    def test_logged_out_show_user(self):
        """tests that user who isn't logged in can't view anothe ruser"""
        with app.test_client() as client:
            resp = client.get(f'/users/{self.u1_id}', follow_redirects=True)

            html = resp.get_data(as_text=True)
            self.assertEqual(resp.status_code, 200)
            self.assertIn("Access unauthorized", html)
            self.assertIn("Log in", html)
            self.assertIn("New to Warbler", html)

    def test_valid_signup(self):
        """tests that user can signup with valid credentials"""
        with app.test_client() as client:
            resp = client.post('/signup',
                               data={
                                   "username": "u200",
                                   "password": "anypassword",
                                   "email": "z1@z1.com",
                                   "image_url": ""
                               },
                               follow_redirects=True)

            html = resp.get_data(as_text=True)
            self.assertEqual(resp.status_code, 200)
            self.assertIn("@u200", html)

    def test_invalid_signup_username(self):
        """tests that user can't signup with invalid username"""
        with app.test_client() as client:
            resp = client.post('/signup',
                               data={
                                   "username": "u1",
                                   "password": "anypassword",
                                   "email": "z@z.com",
                                   "image_url": ""
                               })
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("Username already exists.", html)

    def test_invalid_signup_email(self):
        """tests that user can't signup with invalid email"""

        with app.test_client() as client:
            resp = client.post('/signup',
                               data={
                                   "username": "u12",
                                   "password": "anypassword",
                                   "email": "u1@email.com",
                                   "image_url": ""
                               })
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("Email already exists.", html)

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
        """Tests user following page has all the people they follow"""

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
        """Tests that user follower page has all their followers"""

        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            u1 = User.query.get(self.u1_id)
            u2 = User.query.get(self.u2_id)

            u2.following.append(u1)

            resp = client.get(f'/users/{self.u1_id}/followers')
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("@u2", html) #TODO: consider using a 3rd user

    def test_logged_out_follower_view(self):
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
            self.assertIn("Log in", html)
            self.assertIn("New to Warbler", html)

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

            # tests that following counter has incremented up
            self.assertIn(f"""<li class="stat">
            <p class="small">Following</p>
            <h4>
              <a href="/users/{self.u1_id}/following">
                1
              </a>
            </h4>
          </li>""", html)

    def test_logged_out_follow(self):
        """Tests that logged out user can't view follow page"""

        with app.test_client() as client:

            resp = client.post(f'/users/follow/{self.u2_id}',
                               follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn('Access unauthorized.', html)
            self.assertIn("Log in", html)
            self.assertIn("New to Warbler", html)

    def test_unfollow_user(self):
        """Tests that user can correctly unfollow another user"""

        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            u1 = User.query.get(self.u1_id)
            u2 = User.query.get(self.u2_id)

            # u1 is now following u2
            u1.following.append(u2)

            resp = client.post(f'/users/stop-following/{self.u2_id}',
                               follow_redirects=True)

            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertEqual(u2.is_followed_by(u1), False)

            # tests that following counter has incremented down
            self.assertIn(f"""<li class="stat">
            <p class="small">Following</p>
            <h4>
              <a href="/users/{self.u1_id}/following">
                0
              </a>
            </h4>
          </li>""", html)

    def test_logged_out_unfollow(self):
        """Tests that a user who isn't logged in can't unfollow another user"""

        with app.test_client() as client:
            # user not logged in
            resp = client.post(f'/users/stop-following/{self.u2_id}',
                               follow_redirects=True)

            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn('Access unauthorized.', html)
            self.assertIn("Log in", html)
            self.assertIn("New to Warbler", html)

    def test_delete_user(self):
        """test if logged in user can delete their profile and is logged out"""

        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            resp = client.post(f"/users/delete", follow_redirects=True)

            html = resp.get_data(as_text=True)

            self.assertIn('User has been deleted, goodbye!', html)
            # querying for a deleted user should give back None
            self.assertEqual(User.query.get(self.u1_id), None)

    def test_logged_out_delete_user(self):
        """Tests that a user who isn't logged in can't delete own account"""

        with app.test_client() as client:
            # user not logged in
            resp = client.post(f"/users/delete", follow_redirects=True)

            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn('Access unauthorized.', html)
            self.assertIn("Log in", html)
            self.assertIn("New to Warbler", html)

    def test_update_profile(self):
        """tests to see if the user can change their profile using valid
        form inputs"""
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            resp = client.post('/users/profile',
                            data={"username": "newName",
                                    "email": "new@email.com",
                                    "bio": "this is the new me.",
                                    "password": "password"},
                            follow_redirects=True
                            )

            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("@newName", html)
            self.assertIn("this is the new me", html)

    def test_invalid_profile_update_password(self):
        """tests to see if the user can change their profile using a wrong
        password"""
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            resp = client.post('/users/profile',
                            data={"username": "newName",
                                    "email": "new@email.com",
                                    "bio": "this is the new me.",
                                    "password": "wrongpassword"},
                            )

            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("Wrong password", html)

    def test_invalid_username_update(self):
        """Tests to see if a user tries to update their username with one that
        already exists"""
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

        resp = client.post('/users/profile',
                           data={"username": "u2",
                                 "email": "u1@email.com",
                                 "password": "password"},
                           follow_redirects=True
                           )

        html = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 200)
        self.assertIn("Username already exists.", html)

    def test_display_user_update_page(self):
        """Tests to see if the user edit page is rendered with existing
        user info"""
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            resp = client.get('/users/profile')
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("Edit Your Profile.", html)
            self.assertIn('value="u1"', html)
            self.assertIn('value="u1@email.com"', html)

    def test_logged_out_display_user_update_page(self):
        """Tests to see if a user who isn't logged in gets redirected if trying
        to access the edit profile page"""
        with app.test_client() as client:
            resp = client.get('/users/profile', follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("Access unauthorized.", html)
            self.assertIn("Log in", html)
            self.assertIn("New to Warbler", html)

    def test_valid_logout(self):
        """Tests to see if a user can log out and be sent to the login page"""
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            u1 = User.query.get(self.u1_id)

            resp = client.post('/logout', follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn(f'{u1.username} successfully logged out!', html)

    def test_invalid_logout(self):
        """Tests to see if a user who is not logged in will be rejected
        and redirected if they try to logout"""
        with app.test_client() as client:
            resp = client.post('/logout', follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("Access unauthorized.", html)

    def test_user_page(self):
        """Tests to see if all users page is rendered"""
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            resp = client.get('/users')
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("@u1", html)
            self.assertIn("@u2", html)

    def test_search_user_page(self):
        """Tests to see users page is rendered for a search query"""
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            resp = client.get('/users', query_string={"q": "u2"})
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("@u2", html)
            self.assertNotIn("@u1", html)


    def test_logged_out_user_page(self):
        """Tests to see if a user who is not logged in will be redirected
        if they try to view user page"""
        with app.test_client() as client:

            resp = client.get('/users', follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("Access unauthorized.", html)
            self.assertIn("Log in", html)
            self.assertIn("New to Warbler", html)

    def test_logged_out_following_page(self):
        """Tests to see if a user who is not logged in will be redirected
        if they try to view user following page"""
        with app.test_client() as client:

            resp = client.get(
                f'/users/{self.u1_id}/following', follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("Access unauthorized.", html)
            self.assertIn("Log in", html)
            self.assertIn("New to Warbler", html)

    def test_user_likes(self):
        """Tests to see if a user who is not logged in will be redirected
        if they try to view user likes page"""
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            u1 = User.query.get(self.u1_id)
            m2 = Message.query.get(self.m2_id)

            u1.liked_messages.add(m2)

            resp = client.get(f'/users/{self.u1_id}/likes', follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("m2-text", html)
            self.assertIn("bi-heart-fill", html)
            self.assertIn("@u2", html)

    def test_logged_out_like_page(self):
        """Tests to see if a user who is not logged in will be redirected
        if they try to view user likes page"""
        with app.test_client() as client:

            resp = client.get(
                f'/users/{self.u1_id}/likes', follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("Access unauthorized.", html)
            self.assertIn("Log in", html)
            self.assertIn("New to Warbler", html)
