import os
import mechanize
import pykka


# Static URLs
main_URL = 'https://poshmark.com/'
login_URL = main_URL + 'login'
parties_URL = main_URL + 'parties'
user_URL = main_URL + 'user'


def make_br():
    br = mechanize.Browser()
    br.set_handle_robots(False)   # ignore robots
    br.set_handle_refresh(False)  # can sometimes hang without this
    return br


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class UserFollower(pykka.ThreadingActor):

    def __init__(self):
        super(UserFollower, self).__init__()

        self.br = make_br()
        self.followed_users = set()

        # Get Credentials
        POSHMARK_USER = os.getenv('POSHMARKUSER')
        POSHMARK_PASS = os.getenv('POSHMARKPASS')

        # Log in
        self.br.open(login_URL)
        self.br.select_form(nr=2)
        self.br['login_form[username_email]'] = POSHMARK_USER
        self.br['login_form[password]'] = POSHMARK_PASS
        self.br.submit()
        print 'Logged in'
        print ''

    def on_receive(self, message):
        try:
            username = message['username']
        except:
            print 'invalid message to UserFollower: ' + message
        if username not in self.followed_users:
            self.follow_user(message['username'])

    def follow_user(self, user):
        followers_url = user_URL + '/' + user + '/' + 'followers'
        self.br.open(followers_url)

        if self.br.links(text_regex='^Follow$'):
            try:
                self.br.follow_link(text_regex='^Follow$', nr=1)
            except Exception as e:
                print str(e)
                raise e

        else:
            print 'no follow link'

        self.followed_users.add(user)
        print '{}{}{}\t{}'.format(bcolors.OKGREEN, len(self.followed_users), bcolors.ENDC, user)


class UserFinder(pykka.ThreadingActor):

    def __init__(self, follower):
        super(UserFinder, self).__init__()
        self.br = make_br()
        self.follower = follower

    def begin(self):
        self.br.open(parties_URL)
        party_links = self.br.links(text_regex='.*Party.*')
        for link in list(party_links):
            for user in self.get_usernames(link):
                try:
                    self.send_user(user)
                except:
                    print ''
                    print 'ERROR'
                    print 'Could not follow ' + user
                    print 'Log on to poshmark and tell them you are human (heh)'

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
        self.follower.tell({'username': user})
        for username in self.find_following(user):
            self.follower.tell({'username': user})

