import unittest
import subprocess
import os


class ScraperTests(unittest.TestCase):
    def test_email_scraper(self):
        # Runs the test spider and pipes the printed output to "output"
        os.chdir(os.path.join(os.pardir, os.pardir))
        p = subprocess.Popen('scrapy crawl email_scraper_test', stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        output, error = p.communicate()

        # Splits the results based on automatically added characters
        emails = output.splitlines()
        emails = emails[:len(emails)-1]

        # Hardcoded results based on the sites that were crawled
        assert_list = ["sgnhrc@nic.in",
                       "covdnhrc@nic.in",
                       "anilpradhanshilong@gmail.com",
                       "snarayan1946@gmail.com",
                       "tvarghese@bombayteenchallenge.org"]

        for test in assert_list:
            self.assertIn(test, emails, "Email " + test + "not found")

    def test_link_scraper(self):
        p = subprocess.Popen('scrapy crawl link_scraper_test', stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        output, error = p.communicate()
        urls = output.splitlines()
        urls = [x.lower() for x in urls]

        assert_list = ["http://www.black.com/"
                       ]

        for test in assert_list:
            self.assertIn(test.lower(), urls, "URL " + test + " was not found")

    def test_keyword_scraper(self):
        # Runs the test spider and pipes the printed output to "output"
        p = subprocess.Popen('scrapy crawl keyword_scraper_test', stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        output, error = p.communicate()
        # Splits the results based on automatically added characters
        #keywords = output.split("\r\n")
        #keywords = keywords[:len(keywords)-1]
        keywords = output

        assert_list = ["nicolas", "cage"]
        for test in assert_list:
            self.assertIn(test, keywords, "Keyword " + test + " not found or frequent enough")

if __name__ == '__main__':
    try:
        unittest.main()
    except SystemExit as inst:
        if inst.args[0]:
            raise