import sys
import pykka
from resources import UserFinder, UserFollower, Printer


def stop():
    print ''
    print 'Error detected. Ending Crawl'
    pykka.ActorRegistry.stop_all()
    sys.exit(0)

def main():

    number_of_followers = 2
    try:
        number_of_followers = int(sys.argv[1])
    except:
        pass

    printer = Printer.start()

    if number_of_followers > 1:
        first_follower = UserFollower.start(printer=printer, exit_function=stop)
        cookiejar = first_follower.proxy().br.get()._ua_handlers['_cookies'].cookiejar
        followers = [UserFollower.start(
            cookies=cookiejar, printer=printer, exit_function=stop) for _ in range(number_of_followers-1)]
        followers.append(first_follower)
    else:
        followers = [UserFollower.start(printer=printer, exit_function=stop)]



    print 'starting crawl'
    finder = UserFinder.start(followers=followers)
    finder.proxy().begin()

if __name__ == '__main__':
    main()
