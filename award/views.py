from django.core.exceptions import FieldError
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import render, reverse, get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views import generic
from markdown import markdown

from .forms import SubmissionForm, RenewTokenForm
from .models import Lecturer, Verification, Nomination


class LecturerListView(generic.ListView):
    model = Lecturer

    def post(self, request, *args, **kwargs):
        request.session['has_dismissed_language_info'] = True
        return HttpResponseRedirect(reverse('lecturer-list'))

    def get_queryset(self):
        query = Lecturer.objects.filter(
            nomination__is_verified=True
        ).distinct()
        search = self.request.GET.get('q')
        if search:
            for word in search.split(' '):
                try:
                    query = query.filter(
                        Q(first_name__unaccent__lower__trigram_search=word) |
                        Q(last_name__unaccent__lower__trigram_search=word)
                    )
                except FieldError:
                    query = query.filter(
                        Q(first_name__icontains=word) | Q(last_name__icontains=word)
                    )
        return query.order_by('faculty', 'first_name', 'last_name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['stats'] = {
            'votes': Nomination.objects.count(),
            'votes_verified': Nomination.objects.filter(is_verified=True).count(),
            'unique_users': Nomination.objects.values('sub_email').distinct().count(),
        }
        context['desc'] = markdown(_("The **Teaching Award of the Student Body** honors lecturers with outstanding "
                                     "teaching. In particular, the conversion of their own teaching to digital means "
                                     "and the provision of additional teaching for students, due to the current "
                                     "pandemic situation, should be recognized. Not only professors can be nominated, "
                                     "but also any person who offers teaching at "
                                     "[Otto-von-Guericke-University Magdeburg](https://www.ovgu.de), e.g. lecturers "
                                     "or internship supervisors.\n"
                                     "\n"
                                     "The submitted nominations will be discussed at a meeting of the Student Council "
                                     "after the **submission deadline (%(month)s %(day)s, %(year)s)**, where the "
                                     "final winners will also be selected. In this process, the reasons submitted "
                                     "during the nomination process shall be predominantly included in the selection "
                                     "of the winners and the number of signed students shall only play a secondary "
                                     "role. In this way, we also want to give modules with a low number of "
                                     "participants an equal chance to have their "
                                     "teacher recognized.") % {'year': "2021", 'month': _("June"), 'day': "20"})
        return context


class SubmissionFormView(generic.FormView):
    form_class = SubmissionForm
    template_name = 'award/submission_form.html'
    success_url = 'success/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['privacy'] = markdown(_("We need your email address to confirm your identity and prevent "
                                        "misrepresentation. The personal data will always be treated confidentially "
                                        "and will not be passed on to third parties. All submitted proposals will be "
                                        "kept for **a maximum of 6 months** and then irrevocably deleted."))
        return context

    def get_initial(self):
        initial = super().get_initial()
        initial.update(self.request.GET.dict())
        return initial

    def form_valid(self, form):
        form.save(self.request)
        return super().form_valid(form)


class SubmissionSuccessView(generic.TemplateView):
    template_name = 'award/success.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['feedback'] = markdown(
            _("We have successfully received your nomination. **The last step is to confirm your "
              "nomination by clicking on the link we just sent you by email.** If you want to "
              "submit more nominations or sign already existing ones you can simply return to "
              "the [home page](%(url)s).") % {'url': reverse('lecturer-list')})
        return context


def verify_token(request, token):
    try:
        verification = Verification.objects.get(pk=token)
    except Verification.DoesNotExist:
        feedback = {
            'valid_token': False,
            'title': _("Token does not exist"),
            'message': _("The link you used is broken or outdated. Please use "
                         "only the link you received from us by email."),
        }
        return render(request, 'award/verification.html', {'feedback': feedback})

    if timezone.now() > verification.expiration:
        expiry = timezone.make_naive(verification.expiration)
        feedback = {
            'valid_token': False,
            'title': _("Token is expired"),
            'message': _("The link used was only valid until %(expiry)s.") % {'expiry': expiry},
            'token_expired': True,
            'sub_email': verification.nomination.get_valid_email(),
        }
        return render(request, 'award/verification.html', {'feedback': feedback})

    nomination = verification.nomination
    verification.delete()

    nomination.is_verified = True
    nomination.save()

    lecturer = nomination.lecturer

    feedback = {
        'valid_token': True,
        'title': _("Token is valid"),
        'message': _("Your nomination for %(lecturer)s has been successfully confirmed.") % {
            'lecturer': lecturer.get_full_name()
        }
    }

    return render(request, 'award/verification.html', {'feedback': feedback})


class RenewTokenView(generic.FormView):
    form_class = RenewTokenForm
    template_name = 'award/renew_token.html'
    success_url = 'success/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['privacy'] = markdown(_("The entered email address is **not stored** by us. "
                                        "We will only use it for sending the required emails."))
        return context

    def get_initial(self):
        initial = super().get_initial()
        initial.update(self.request.GET.dict())
        return initial

    def form_valid(self, form):
        form.renew_tokens(self.request)
        return super().form_valid(form)


class RenewTokenSuccessView(generic.TemplateView):
    template_name = 'award/success.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['feedback'] = markdown(_("We have just sent you a new email with a valid confirmation link for all "
                                         "open nominations. **Any old emails with a confirmation link that you "
                                         "still have in your inbox are no longer valid.**"))
        return context


@login_required
def toggle_favorite_lecturer(request, pk):
    lecturer = get_object_or_404(Lecturer, pk=pk)

    if request.method == 'POST':
        value = request.POST.get('is-favorite', 'no')
        if value == 'no':
            lecturer.is_favorite = True
        else:
            lecturer.is_favorite = False
        lecturer.save()

    context = {
        'lecturer': lecturer,
        'nominations': lecturer.nomination_set.count(),
        'nominations_verified': lecturer.nomination_set.filter(is_verified=True).count(),
    }

    return render(request, 'award/lecturer_detail.html', context)


class LecturerSelectView(LoginRequiredMixin, generic.ListView):
    model = Lecturer
    ordering = ('first_name', 'last_name')
    template_name = 'award/lecturer_select.html'

    def get_queryset(self):
        query = Lecturer.objects.distinct()
        faculty = self.request.GET.get('faculty')
        if faculty:
            query = query.filter(faculty=faculty)
        return query

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['faculties'] = Lecturer.FACULTIES
        context['faculty_selected'] = self.request.GET.get('faculty')
        return context
