# vehicles/forms.py
from .models import Brand

class BrandForm(forms.ModelForm):
    class Meta:
        model = Brand
        fields = ['name', 'logo']
class DashboardHomeView(AdminRequiredMixin, LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/home.html'
