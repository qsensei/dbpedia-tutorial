import json
import os
import subprocess
import tempfile
import time

import splinter
import xvfbwrapper


class BaseTest(object):
    def setup(self):
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
            'College', 'High School', 'Draft Year'
        }
        if ignore:
            facets -= ignore
        for facet in facets:
            xpath = self.facet(facet)
            assert self.browser.is_element_present_by_xpath(xpath)


class TestUpload(BaseTest):
    def assert_sports_populated(self):
        for sport in ('Basketball', 'Baseball', 'Football'):
            self.browser.visit(self.baseurl)
            self.assert_facets_occupied()
            n_athletes = self.get_facet_value_frequency('Type', 'Athlete')
            self.click_facet_value('Sport', sport)
            response = self.get_facet_value_frequency('Type', 'Athlete')
            assert response < n_athletes
            self.assert_facets_occupied(ignore={'Sport'})

    def test_setup_from_dl_file(self):
        self.run_invoke('setup')
        self.assert_sports_populated()

    def test_fresh_dump(self):
        _, filename = tempfile.mkstemp()
        os.environ['PEOPLE_JSON'] = filename
        os.environ['PEOPLE_DUMP_LIMIT'] = str(5000)
        try:
            self.run_invoke('setup_fuse')
            self.run_script('scripts/dump_athletes.py')
            # should be a valid JSON
            with open(filename) as f:
                data = json.load(f)
                # should dump in chunks of 2000
                assert len(data['items']) <= 6000
            self.run_script('scripts/upload_athletes.py')
            self.assert_sports_populated()
        finally:
            os.remove(filename)
            os.environ.pop('PEOPLE_JSON')
            os.environ.pop('PEOPLE_DUMP_LIMIT')
