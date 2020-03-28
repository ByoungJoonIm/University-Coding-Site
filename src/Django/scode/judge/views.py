# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render, redirect

from django.views.generic import ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView, FormView
from django.urls import reverse_lazy

from django.views.generic.base import TemplateView
#from .forms import PostForm

from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from django.db import connection

from django.contrib.auth.models import User, Group
from django.contrib.auth.mixins import LoginRequiredMixin

from judge.models import *
from judge.forms import AssignmentForm, CodingForm


from judge.judgeManager import JudgeManager
from scode.loginManager import LoginManager

import pymysql
import os
import pathlib
import datetime


#-- Here is developing area    
# common area 
class UserMainLV(LoginRequiredMixin, ListView):
    template_name = 'judge/common/common_subject_list.html'
    
    def get(self, request, *args, **kwargs):
        signup_class = Signup_class.objects.filter(user_id=self.request.user.id).values_list('subject_id')
        subject = Subject.objects.filter(pk__in = signup_class)
        
        return render(request, self.template_name, { 'subject' : subject })
    
class AssignmentLV(LoginRequiredMixin, ListView):
    template_name = 'judge/common/common_assignment_list.html'
    paginate_by = 10
    
    def post(self, request, *args, **kwargs):
        subject_id = request.POST.get('subject_id')
        request.session['subject_id'] = subject_id
        
        return self.get(request, args, kwargs)

    @classmethod
    def get(self, request, *args, **kwargs):
        if('subject_id' not in request.session):
            return redirect(reverse_lazy('judge:common_subject_list'))
        
        subject_id = request.session.get('subject_id')
        assignment = Assignment.objects.filter(subject_id = subject_id)
        subject = Subject.objects.get(id = subject_id)
        
        return render(request, self.template_name, { 'assignment' : assignment, 'subject' : subject })
    
# professor area

class ProfessorAddView(LoginRequiredMixin, FormView):
    template_name = 'judge/professor/professor_assignment_add.html'
    form_class = AssignmentForm

    def form_valid(self, form):
        # return render(self.request, self.template_name, {'form': self.form})
        return super().form_valid(form)

    # def handle_uploaded_file(self, files, path):
    #     uploaded_file_name = ['in', 'out']
    #     for f in files:
    #         with open(path + '/temp/' + uploaded_file_name[files.index(f)], 'wb+') as dest:
    #             for chunk in f.chunks():
    #                 dest.write(chunk)

    def handle_file_construct(self, subject_id):
        subject = Subject.objects.get(id = subject_id)

    # def post(self, request, *args, **kwargs):
    #     judgeManager = JudgeManager()
    #     judgeManager.construct(request.session['professor_id'])
    #     base_file_path = judgeManager.get_file_path(request.session['subject_id'], request.session['professor_id'])
    #     self.handle_uploaded_file([request.FILES['in_file'], request.FILES['out_file']], base_file_path)

    #     #judgeManager.create_problem(request.session['professor_id'], request.session['subject_id'])
    #     judgeManager.add_assignment(request.session['subject_id'], request.POST.get('assignment_name'),
    #             request.POST.get('assignment_desc'), int(request.POST.get('deadline')))


    #     # we need next step which is inserting db.

    #     return redirect(reverse_lazy('judge:subject', args=[request.session['title'], request.session['classes']]))

    def post(self, request, *args, **kwargs):
        if("assignment_name" in request.POST):  # submit it self
            if("subject_id" in request.session):
                return AssignmentLV.get(request, args, kwargs)
            return redirect(reverse_lazy('judge:common_subject_list'))
        else:
            print("not found!")    
            
        return render(request, self.template_name, {'form' : self.form_class})
        
#class ProfessorUpdateView(UpdateView):
class ProfessorUpdateView(LoginRequiredMixin, TemplateView):
    template_name = 'judge/professor/professor_assignment_update.html'
    
    def post(self, request, * args, **kwarges):
        return render(request, self.template_name)


# student area
#-----------------------I'm working here.
class StudentAssignment(LoginRequiredMixin, FormView):
    template_name = 'judge/student/student_assignment.html'
    form_class = CodingForm

    def post(self, request, * args, **kwarges):
        return render(request, self.template_name)

'''
# This page shows result of a assiginment.
class ProfessorResultLV(ListView, LoginManager):
    # We need to revise sub_seq_id
    sub_seq_id = 2
    sql = 'SELECT judge_student.student_id,judge_student.student_name,score \
            FROM judge_student,judge_submit,judge_assignment \
            WHERE judge_assignment.sub_seq_id = judge_submit.sub_seq_id \
            AND judge_student.student_id = judge_submit.student_id \
            AND judge_assignment.sequence = judge_submit.sequence_id \
            AND judge_submit.sub_seq_id = ' + str(sub_seq_id) + ';'

    queryset = Student.objects.raw(sql)
    template_name = 'judge/professor/professor_result_list.html'
    context_object_name = "objects"

class ProfessorCreateView(FormView, LoginManager):
    template_name = 'judge/professor/professor_assignment_add.html'
    form_class = AssignmentForm

#    def form_valid(self, form):
        #return render(self.request, self.template_name, {'form': self.form})
#        return super().form_valid(form)

    def handle_uploaded_file(self, files, path):
        uploaded_file_name = ['in', 'out']
        for f in files:
            with open(path + '/temp/' + uploaded_file_name[files.index(f)], 'wb+') as dest:
                for chunk in f.chunks():
                    dest.write(chunk)

    def post(self, request, *args, **kwargs):
        judgeManager = JudgeManager()
        judgeManager.construct(request.session['professor_id'])
        base_file_path = judgeManager.get_file_path(request.session['subject_id'], request.session['professor_id'])
        self.handle_uploaded_file([request.FILES['in_file'], request.FILES['out_file']], base_file_path)

        #judgeManager.create_problem(request.session['professor_id'], request.session['subject_id'])
        judgeManager.add_assignment(request.session['subject_id'], request.POST.get('assignment_name'),
                request.POST.get('assignment_desc'), int(request.POST.get('deadline')))


        # we need next step which is inserting db.

        return redirect(reverse_lazy('judge:subject', args=[request.session['title'], request.session['classes']]))


#class ProfessorUpdateView(UpdateView):
class ProfessorUpdateView(TemplateView, LoginManager):
    template_name = 'judge/professor/professor_assignment_update.html'

#class ProfessorDeleteView(DeleteView):
class ProfessorDeleteView(TemplateView, LoginManager):
    template_name = 'judge/professor/professor_assignment_delete.html'

#class ProfessorSettingsView(UpdateView):
class ProfessorSettingsView(TemplateView, LoginManager):
    template_name = 'judge/professor/professor_subject_settings.html'

'''
'''
class StudentSubjectLV(TemplateView, LoginManager):
    queryset = None
    template_name = 'judge/student/student_subject_list.html'

    def common(self, request):
        if request.session['subject_id']:
            now = datetime.datetime.now()
            common_sql = ' \
                    SELECT sequence, assignment_name, lf.student_id, deadline, score, max_score \
                    FROM ( \
                    SELECT sequence, assignment_name, judge_student.student_id, deadline, max_score, judge_assignment.sub_seq_id \
                    FROM judge_student \
                    INNER JOIN (judge_signup_class, judge_assignment) \
                    ON (judge_student.student_id = judge_signup_class.student_id \
                    AND judge_signup_class.sub_seq_id = judge_assignment.sub_seq_id) \
                    WHERE judge_assignment.sub_seq_id = {0} \
                    AND judge_student.student_id = "{1}" \
                    AND judge_assignment.sub_seq_id = {0}) as lf \
                    LEFT JOIN judge_submit \
                    ON (lf.sequence = judge_submit.sequence_id \
                    AND lf.student_id = judge_submit.student_id \
                    AND lf.sub_seq_id = judge_submit.sub_seq_id) \
                    WHERE deadline '.format(request.session["subject_id"], request.session['student_id'])

            not_expired_assignment_list_sql = common_sql + '> "{0}";'.format(now)
            expired_assignment_list_sql = common_sql + '< "{0}";'.format(now)

            not_expired_assignment_list = Student.objects.raw(not_expired_assignment_list_sql)
            expired_assignment_list = Student.objects.raw(expired_assignment_list_sql)

            return render(request, self.template_name,
                    { 'not_expired_assignment_list': not_expired_assignment_list,
                      'expired_assignment_list': expired_assignment_list })
        else:
            return HttpResponse('This is wrong way!')


    def get(self, request, *args, **kwargs):
        return self.common(request)

    def post(self, request, *args, **kwargs):
        form = request.POST
        request.session['title'] = form.get('title')
        request.session['classes'] = form.get('classes')
        request.session['subject_id'] = form.get('subject_id')

        return self.common(request)

class StudentAssignment(FormView, LoginManager):
    template_name = 'judge/student/student_assignment.html'
    form_class = CodingForm

    def post(self, request, *args, **kwargs):
        judgeManager = JudgeManager()
        sequence = request.POST.get('sequence')
        
        # into assignment page
        if sequence:
            lang_name = judgeManager.get_lang_name(
                    judgeManager.get_lang_pri_key(request.session['subject_id']))
            assign_info = { 
                'lang': lang_name, 
                'name': judgeManager.get_assign_name(request.session['subject_id'], sequence), 
                'desc': judgeManager.get_assign_desc(request.session['subject_id'], sequence) 
            }
            request.session['sequence'] = sequence
            return render(request, self.template_name, {'assign_info': assign_info, 'form': CodingForm})

        # submit assignment
        else:
            judgeManager = JudgeManager()
            form = CodingForm(request.POST)
            sequence = request.session['sequence']
            del request.session['sequence']

            if form.is_valid():
                code = form.cleaned_data['code']
                code = code.encode('utf-8')
                judgeManager.create_src_file(code, request.session['student_id'], request.session['subject_id'], sequence)
                # we are here
                judgeManager.judge(request.session['subject_id'], request.session['student_id'], sequence)

            return redirect(reverse_lazy('judge:std_subject', args=[request.session['title'], request.session['classes']]))

'''