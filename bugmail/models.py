from django.db import models
from django.utils.timezone import now


class BugmailStatManager(models.Manager):
    def stats_for_range(self, start, stop=None):
        stats = self.filter(date__gte=start)
        if stop is not None:
            stats = stats.filter(date__lte=stop)
        return stats


class BugmailStat(models.Model):
    TOTAL = 1
    USED = 2
    TYPE_CHOICES = (
        (TOTAL, 'Total'),
        (USED, 'Used'),
    )

    stat_type = models.PositiveSmallIntegerField(choices=TYPE_CHOICES)
    count = models.PositiveSmallIntegerField()
    date = models.DateField(default=now)

    objects = BugmailStatManager()

    class Meta:
        ordering = ('date',)
