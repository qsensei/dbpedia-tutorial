import os
import subprocess
import time

import splinter
import xvfbwrapper


class BaseTest(object):
    def setup(self):
        self.run_invoke('setup_fuse')
        self.xvfb = xvfbwrapper.Xvfb()
        self.xvfb.start()
        self.browser = splinter.Browser('firefox')

    def teardown(self):
        self.browser.quit()
        self.xvfb.stop()
        self.run_invoke('teardown')

    @property
    def docker_host(self):
        return os.environ.get('DOCKER_HOST', '127.0.0.1')

    @property
    def baseurl(self):
        return 'http://%s:8000' % self.docker_host

    def run_script(self, script):
        with open(os.devnull, 'w') as f:
            subprocess.check_call(['bin/python', script], stdout=f)
        time.sleep(1)

    def run_invoke(self, task):
        with open(os.devnull, 'w') as f:
            subprocess.check_call(['bin/inv', task], stdout=f)
        time.sleep(1)

    def facet(self, facet):
        xpath = '//aside[contains(@class,"search-results-panel")]'
        xpath += '/div/section/section[//h1="%s"]' % facet
        return xpath

    def facet_value(self, facet, value):
        xpath = self.facet(facet)
        xpath += '/div/ul/li[strong[@title="%s"]]' % value
        return xpath

    def get_facet_value_frequency(self, facet, value):
        xpath = '//aside[contains(@class,"search-results-panel")]'
        xpath += '/div/section/section[//h1="%s"]' % facet
        xpath += '/div/ul/li[strong[@title="%s"]]' % value
        xpath += '/span[contains(@class,"number")]'
        return int(self.browser.find_by_xpath(xpath)
                       .first.value.replace(',', ''))

    def click_facet_value(self, facet, value, will_disappear=True):
        xpath = self.facet_value(facet, value)
        self.browser.is_element_present_by_xpath(xpath)
        self.browser.find_by_xpath(xpath).first.click()
        if will_disappear:
            assert self.browser.is_element_not_present_by_xpath(
                xpath, wait_time=10)

    def assert_facets_occupied(self, ignore=None):
        facets = {
            'Team', 'Sport', 'Position', 'Player', 'Birth Year', 'Birth Place',
            'College', 'Location', 'High School', 'Draft Year'
        }
        if ignore:
            facets -= ignore
        for facet in facets:
            xpath = self.facet(facet)
            assert self.browser.is_element_present_by_xpath(xpath)


class TestScripts(BaseTest):
    def test_football(self):
        self.run_script('scripts/upload_football.py')
        self.browser.visit(self.baseurl)
        self.assert_facets_occupied()
        n_athletes = self.get_facet_value_frequency('Type', 'Athlete')
        # find and click on sport:"Football"
        self.click_facet_value('Sport', 'Football')
        # make sure we have at least 100 athletes
        assert self.get_facet_value_frequency('Type', 'Athlete') == n_athletes
        self.assert_facets_occupied(ignore={'Sport'})

    def test_baseball(self):
        self.run_script('scripts/upload_baseball.py')
        self.browser.visit(self.baseurl)
        self.assert_facets_occupied()
        n_athletes = self.get_facet_value_frequency('Type', 'Athlete')
        # find and click on sport:"Baseball"
        self.click_facet_value('Sport', 'Baseball')
        # make sure we have at least 100 athletes
        assert self.get_facet_value_frequency('Type', 'Athlete') == n_athletes
        self.assert_facets_occupied(ignore={'Sport'})

    def test_basketball(self):
        self.run_script('scripts/upload_basketball.py')
        self.browser.visit(self.baseurl)
        self.assert_facets_occupied()
        n_athletes = self.get_facet_value_frequency('Type', 'Athlete')
        # find and click on sport:"Basketball"
        self.click_facet_value('Sport', 'Basketball')
        # make sure we have at least 100 athletes
        assert self.get_facet_value_frequency('Type', 'Athlete') == n_athletes
        self.assert_facets_occupied(ignore={'Sport'})


class TestSetupTask(BaseTest):
    def setup(self):
        self.xvfb = xvfbwrapper.Xvfb()
        self.xvfb.start()
        self.browser = splinter.Browser('firefox')

    def test_combination(self):
        self.run_invoke('setup')
        for sport in ('Basketball', 'Baseball', 'Football'):
            self.browser.visit(self.baseurl)
            self.assert_facets_occupied()
            n_athletes = self.get_facet_value_frequency('Type', 'Athlete')
            self.click_facet_value('Sport', sport)
            response = self.get_facet_value_frequency('Type', 'Athlete')
            assert response < n_athletes
            self.assert_facets_occupied(ignore={'Sport'})
