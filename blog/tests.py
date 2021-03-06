from datetime import timedelta
from test.support import captured_stderr

from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils import timezone

from .models import Entry, Event


class DateTimeMixin(object):
    def setUp(self):
        self.now = timezone.now()
        self.yesterday = self.now - timedelta(days=1)
        self.tomorrow = self.now + timedelta(days=1)


class EntryTestCase(DateTimeMixin, TestCase):
    def test_manager_active(self):
        """
        Make sure that the Entry manager's `active` method works
        """
        Entry.objects.create(pub_date=self.now, is_active=False, headline='inactive')
        Entry.objects.create(pub_date=self.now, is_active=True, headline='active')

        self.assertQuerysetEqual(Entry.objects.published(), ['active'], transform=lambda entry: entry.headline)

    def test_manager_published(self):
        """
        Make sure that the Entry manager's `published` method works
        """
        Entry.objects.create(pub_date=self.yesterday, is_active=False, headline='past inactive')
        Entry.objects.create(pub_date=self.yesterday, is_active=True, headline='past active')
        Entry.objects.create(pub_date=self.tomorrow, is_active=False, headline='future inactive')
        Entry.objects.create(pub_date=self.tomorrow, is_active=True, headline='future active')

        self.assertQuerysetEqual(Entry.objects.published(), ['past active'], transform=lambda entry: entry.headline)

    def test_docutils_safe(self):
        """
        Make sure docutils' file inclusion directives are disabled by default.
        """
        with captured_stderr() as self.docutils_stderr:
            entry = Entry.objects.create(
                pub_date=self.now, is_active=True, headline='active', content_format='reST',
                body='.. raw:: html\n    :file: somefile\n'
            )
        self.assertIn('<p>&quot;raw&quot; directive disabled.</p>', entry.body_html)
        self.assertIn('.. raw:: html\n    :file: somefile', entry.body_html)


class EventTestCase(DateTimeMixin, TestCase):
    def test_manager_past_future(self):
        """
        Make sure that the Event manager's `past` and `future` methods works
        """
        Event.objects.create(date=self.yesterday, pub_date=self.now, headline='past')
        Event.objects.create(date=self.tomorrow, pub_date=self.now, headline='future')

        self.assertQuerysetEqual(Event.objects.future(), ['future'], transform=lambda event: event.headline)
        self.assertQuerysetEqual(Event.objects.past(), ['past'], transform=lambda event: event.headline)

    def test_manager_past_future_include_today(self):
        """
        Make sure that both .future() and .past() include today's events.
        """
        Event.objects.create(date=self.now, pub_date=self.now, headline='today')

        self.assertQuerysetEqual(Event.objects.future(), ['today'], transform=lambda event: event.headline)
        self.assertQuerysetEqual(Event.objects.past(), ['today'], transform=lambda event: event.headline)


class ViewsTestCase(DateTimeMixin, TestCase):
    def test_no_past_upcoming_events(self):
        """
        Make sure there are no past event in the "upcoming events" sidebar (#399)
        """
        # We need a published entry on the index page so that it doesn't return a 404
        Entry.objects.create(pub_date=self.yesterday, is_active=True)
        Event.objects.create(date=self.yesterday, pub_date=self.now, is_active=True, headline='Jezdezcon')
        response = self.client.get(reverse('weblog:index'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['events'], [])
