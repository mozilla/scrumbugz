from django.http import HttpResponse
from django.utils import simplejson as json
from django.views.generic import View

from bugzilla.api import bugzilla


class GetAllProductsView(View):
    def get(self, request):
        products = json.dumps(bugzilla.get_products_simplified())
        return HttpResponse(products, mimetype='application/json')
