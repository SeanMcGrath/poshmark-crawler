import sys
import pykka
from resources import UserFinder, UserFollower, Printer


def main():

    number_of_followers = 2
    try:
        number_of_followers = int(sys.argv[1])
    except:
        pass

    printer = Printer.start()

    if number_of_followers > 1:
        # Log in one follower and use it cookes for all the others
        first_follower = UserFollower.start(printer=printer)
        cookiejar = first_follower.proxy().br.get()._ua_handlers['_cookies'].cookiejar
        followers = [UserFollower.start(
            cookies=cookiejar, printer=printer) for _ in range(number_of_followers-1)]
        followers.append(first_follower)
    else:
        followers = [UserFollower.start(printer=printer)]

    print 'starting crawl'
    for i in range(2):
        finder = UserFinder.start(followers=followers)

if __name__ == '__main__':
    main()
