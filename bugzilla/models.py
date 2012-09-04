from __future__ import absolute_import

import logging

from django.db import models

from .api import bugzilla


log = logging.getLogger(__name__)


class ProductManager(models.Manager):
    def sync_with_bugzilla(self):
        """
        Update products and components from the server.
        """
        prod_set = set()
        comp_set = set()
        products = bugzilla.get_products()
        for p in products['products']:
            prod = self.model(id=p['id'], name=p['name'])
            prod.save()
            prod_set.add(prod)
            for c in p['components']:
                comp = Component(id=c['id'], name=c['name'], product=prod)
                comp.save()
                comp_set.add(comp)
        all_prods = set(self.all())
        all_comps = set(Component.objects.all())
        prods_to_del = [p.id for p in (all_prods - prod_set)]
        comps_to_del = [c.id for c in (all_comps - comp_set)]
        if prods_to_del:
            self.filter(id__in=prods_to_del).delete()
            log.debug('Deleted %d products', len(prods_to_del))
        if comps_to_del:
            Component.objects.filter(id__in=comps_to_del).delete()
            log.debug('Deleted %d components', len(comps_to_del))
        log.info('Synced Products & Components from Bugzilla')


class Product(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True)
    name = models.CharField(max_length=200)

    objects = ProductManager()


class Component(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True)
    name = models.CharField(max_length=200)
    product = models.ForeignKey(Product, related_name='components')
