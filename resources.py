# Classes and functions for poshmark crawling
import os
import random
import traceback
import mechanize
import pykka


# Static URLs
main_URL = 'https://poshmark.com/'
login_URL = main_URL + 'login'
parties_URL = main_URL + 'parties'
user_URL = main_URL + 'user'

# Utility Functions
def noop():
    pass

def make_br():
    br = mechanize.Browser()
    br.set_handle_robots(False)   # ignore robots
    br.set_handle_refresh(False)  # can sometimes hang without this
    return br


class bcolors:
    # Terminal colors
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class UserFollower(pykka.ThreadingActor):
    """
    Actor for following Poshmark users.
    """

    def __init__(self, printer=None, cookies=None, **kwargs):
        """
        :param printer: reference to Printer actor, for output.
        :param cookies: a Cookiejar containing a Poshmark login cookie.
        """
        super(UserFollower, self).__init__(kwargs)

        self.br = make_br()
        self.followed_users = set()
        self.printer = printer

        if cookies:
            self.br.set_cookiejar(cookies)

        else:
            # Get Credentials
            POSHMARK_USER = os.getenv('POSHMARKUSER')
            POSHMARK_PASS = os.getenv('POSHMARKPASS')

            # Log in
            self.br.open(login_URL)
            self.br.select_form(nr=2)
            self.br['login_form[username_email]'] = POSHMARK_USER
            self.br['login_form[password]'] = POSHMARK_PASS
            cookiejar = self.br._ua_handlers['_cookies'].cookiejar
            log_in_response = self.br.submit().read()
            if 'Invalid Username or Password' in log_in_response:
                print 'Failed to Log in'
            else:
                print 'Logged in UserFollower'

    def on_receive(self, message):
        username = message['username']
        if username not in self.followed_users:
            self.follow_user(message['username'])

    def on_failure(self, e_type, e_value, tb):
        if '403' in str(e_value):
            print 'Locked Out: go to Poshmark manually to certify you are human!'
        elif '429' in str(e_value):
            print 'Too many requests: wait a while or use fewer UserFollowers'
        else:
            print str(e_value)
            traceback.print_tb(tb)
        pykka.ActorRegistry.stop_all()
        os._exit()

    def follow_user(self, user):
        followers_url = user_URL + '/' + user + '/' + 'followers'
        self.br.open(followers_url)

        if self.br.links(text_regex='^Follow$'):
            self.br.follow_link(text_regex='^Follow$', nr=1)
        else:
            print 'no follow link'

        self.followed_users.add(user)
        if self.printer:
            self.printer.tell({'username': user})
        else:
            print user


class UserFinder(pykka.ThreadingActor):
    """
    Finds usernames on Poshmark.
    """

    def __init__(self, followers, **kwargs):
        """
        :param followers: a list of references to UserFollowers,
            which follow the users found by this actor.
        """
        super(UserFinder, self).__init__(kwargs)
        self.br = make_br()
        self.followers = followers
        self.curr_follower = 0

        self.begin()

    @property
    def next_follower(self):
        next_follower = self.followers[self.curr_follower]
        self.curr_follower = (self.curr_follower + 1) % len(self.followers)
        return next_follower

    def begin(self):
        self.br.open(parties_URL)
        party_links = list(self.br.links(text_regex='.*Party.*'))
        random.shuffle(party_links)
        for link in party_links:
            for user in self.get_usernames(link):
                self.send_user(user)

    def get_usernames(self, link):
        # find all the usernames at a URL and send them to the follower
        try:
            self.br.open(link)
        except:
            self.br.open(link.url)

        closet_links = [link for link in self.br.links(url_regex='.*closet.*')][1:]
        if closet_links:
            return set([link.url.split('/')[-1] for link in closet_links])
        else:
            return set()

    def find_following(self, user):
        # Find the usernames of every user the given user is following
        following_url = user_URL + '/' + user + '/' + 'following'
        return self.get_usernames(following_url)

    def send_user(self, user):
        self.next_follower.tell({'username': user})
        for username in self.find_following(user):
            self.next_follower.tell({'username': username})


class Printer(pykka.ThreadingActor):

    def __init__(self):
        super(Printer, self).__init__()
        self.number_printed = 0

    def on_receive(self, message):
        try:
            username = message['username']
        except:
            pass

        self.number_printed += 1
        print '{}{}{}\t{}'.format(bcolors.OKGREEN, self.number_printed, bcolors.ENDC, username)

