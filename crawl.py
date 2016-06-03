import sys
from resources import UserFinder, UserFollower


def main():
    print ''
    print 'starting crawl'
    follower = UserFollower.start()
    finder = UserFinder.start(follower=follower)
    finder.proxy().begin()

if __name__ == '__main__':
    main()
