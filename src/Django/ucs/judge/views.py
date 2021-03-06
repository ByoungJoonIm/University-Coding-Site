# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render, redirect

from django.views.generic import ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView, FormView
from django.urls import reverse_lazy

from django.views.generic.base import TemplateView

from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from django.db import connection
from django.db.utils import IntegrityError
from django.db.models import Q, Value, BooleanField

from django.contrib import messages
from django.contrib.auth.models import User, Group

from judge.models import *
from judge.forms import *

import pymysql
import os
import pathlib
import zipfile
import time
import datetime
import subprocess
import yaml
from django.utils import timezone
from ansi2html import Ansi2HTMLConverter

from bs4 import BeautifulSoup

from judge.mixin import ProfessorMixin, StudentMixin
from django.contrib.auth.mixins import LoginRequiredMixin

#-- Here is developing area    
# professor area------------------------------------------------------------------------------------------------------------------------
class ProfessorSubjectLV(ProfessorMixin, ListView):
    template_name = 'judge/professor/professor_subject_list.html'
    
    def get(self, request, *args, **kwargs):
        signup_class = Signup_class_professor.objects.filter(user_id=request.user.id)
        
        q = Q(state=Signup_class_base.State.Accepted) | Q(state=Signup_class_base.State.Owned)
        signup_class_available = signup_class.filter(q)
        signup_class_waiting = signup_class.filter(state=Signup_class_base.State.Waiting) 
        
        return render(request, self.template_name, 
                      { 'signup_class_available' : signup_class_available,
                       'signup_class_waiting' : signup_class_waiting})
    
    def post(self, request, *args, **kwargs):
        form = request.POST
        
        if "accept" in form.keys():
            accept = form.get('accept')
            converter = {"accept" : Signup_class_base.State.Accepted,
                         "reject" : Signup_class_base.State.Rejected,
                         "Accept all" : Signup_class_base.State.Accepted,
                         "Reject all" : Signup_class_base.State.Rejected}
            
            if accept == "accept" or accept == "reject":
                signup_class_professor_instance = Signup_class_professor.objects.get(user=request.user.id, subject=int(form.get("subject_id")))
                signup_class_professor_instance.state = converter.get(accept)
                signup_class_professor_instance.save()
                
            else:   # accept = "Accept all" or "Reject all"
                signup_class_professor = Signup_class_professor.objects.filter(user=request.user).filter(state=Signup_class_base.State.Waiting)
                for scp in signup_class_professor:
                    scp.state = converter.get(accept)
                    scp.save()
            
        elif "hided" in form.keys():
            subject_instance = Subject.objects.get(id=int(request.POST.get('subject_id')))
            subject_instance.hided = True;
            subject_instance.save()
        
        return self.get(request)

class ProfessorSubjectAddView(ProfessorMixin, FormView):
    template_name = 'judge/professor/professor_subject_add.html'
    form_class = SubjectForm
    
    def __randomString(self, stringLength = 8):
        import random, string
        letters = string.ascii_letters +'0123456789'
        return ''.join(random.choice(letters) for i in range(stringLength))
    
    def post(self, request, *args, **kwargs):
        title = request.POST.get('title')
        lang_id = request.POST.get('language')
        
        subject_instance = Subject.objects.create(
            title = title,
            language = Language.objects.get(lang_id=lang_id),
            access_code = self.__randomString()
        )
        
        Signup_class_professor.objects.create(
            subject = subject_instance,
            user = request.user,
            state = Signup_class_base.State.Owned
        )
        
        return redirect(reverse_lazy('judge:professor_subject_list'))

class ProfessorSubjectHidedLV(ProfessorMixin, ListView):
    template_name = 'judge/professor/professor_hided_subject_list.html'
    paginate_by = 10
    
    def get(self, request, *args, **kwargs):
        signup_class = Signup_class_professor.objects.filter(user_id=request.user.id).values_list('subject_id')
        subject = Subject.objects.filter(pk__in = signup_class).filter(hided=True)
        
        return render(request, self.template_name, { 'subject' : subject })
    
    def post(self, request, *args, **kwargs):
        subject = Subject.objects.get(id=int(request.POST.get('subject_id')))
        subject.hided = False;
        subject.save()
        
        return self.get(request)

class ProfessorSubjectManagementView(ProfessorMixin, TemplateView):
    template_name = 'judge/professor/professor_subject_management.html'
    
    def get(self, request, * args, **kwargs):
        
        subject = Subject.objects.get(id = int(request.session.get('subject_id')))
        q = ~Q(state=Signup_class_base.State.Owned)
        participated_professor_list = Signup_class_professor.objects.filter(subject_id=subject.id).filter(q).order_by('state')
        participated_student_list = Signup_class_student.objects.filter(subject=subject.id).filter(q).order_by("-state")
        
        isOwner = Signup_class_professor.objects.get(subject=subject, user=request.user).state == Signup_class_base.State.Owned
    
        return render(request, self.template_name, 
                      {'form' : SubjectForm(initial={'title': subject.title,
                                                     'language': subject.language.lang_id}),
                       'subject' : subject,
                       'participated_professor_list': participated_professor_list,
                       'participated_student_list': participated_student_list,
                       'isOwner' : isOwner
                       }
                      )
        
    def post(self, request, * args, **kwargs):
        form = request.POST
        
        if "invite" in form.keys():
            try:
                Signup_class_professor.objects.create(
                    subject = Subject.objects.get(id=int(request.session.get('subject_id'))),
                    user = User.objects.get(username=form.get('professor_id')),
                    state = Signup_class_base.State.Waiting
                )
            except User.DoesNotExist:
                messages.info(request, "User does not exist")
            except IntegrityError:
                messages.info(request, "You already invited")
            
            return self.get(request)
        elif "revise" in form.keys():
            subject = Subject.objects.get(id = int(request.session.get('subject_id')))
            subject.title = form.get('title')
            subject.language = Language.objects.get(lang_id=form.get('language'))
            subject.save()
        
        elif "accept" in form.keys():
            accept = form.get('accept')
            converter = {"accept" : Signup_class_base.State.Accepted,
                         "reject" : Signup_class_base.State.Rejected,
                         "Accept all" : Signup_class_base.State.Accepted,
                         "Reject all" : Signup_class_base.State.Rejected}
            
            if accept == "accept" or accept == "reject":
                student = User.objects.get(id=int(form.get('student_id')))
                signup_class_student_instance = Signup_class_student.objects.get(user=student, subject=int(request.session.get("subject_id")))
                signup_class_student_instance.state = converter.get(accept)
                signup_class_student_instance.save()
                
            else:   # accept = "Accept all" or "Reject all"
                signup_class_student = Signup_class_student.objects.filter(subject=int(request.session.get("subject_id"))).filter(state=Signup_class_base.State.Waiting)
                for scp in signup_class_student:
                    scp.state = converter.get(accept)
                    scp.save()
                # uppder 3 line maybe same like this
                # signup_class_student.update(state=converter.get(accept))
        
        return self.get(request)

class ProfessorAssignmentLV(ProfessorMixin, ListView):
    template_name = 'judge/professor/professor_assignment_list.html'
    paginate_by = 10
    
    def post(self, request, *args, **kwargs):
        subject_id = request.POST.get('subject_id')
        request.session['subject_id'] = subject_id
        
        return self.get(request, args, kwargs)

    def get(self, request, *args, **kwargs):
        if('subject_id' not in request.session):
            return redirect(reverse_lazy('judge:professor_subject_list'))
        
        subject_id = request.session.get('subject_id')
        assignment = Assignment.objects.filter(subject_id = subject_id)
        subject = Subject.objects.get(id = subject_id)
        
        return render(request, self.template_name, { 'assignment' : assignment, 'subject' : subject })
    
class ProfessorAssignmentResultLV(ProfessorMixin, TemplateView):
    template_name = "judge/professor/professor_assignment_result.html"
    paginate_by = 10
    
    def get(self, request, *args, **kwargs):
        assignment_id = int(request.GET.get('assignment_id'))
    
        signup_student = Signup_class_student.objects.filter(subject=int(request.session.get("subject_id"))).values('user')
        
        submitted_users = Submit.objects.filter(assignment=Assignment.objects.get(id=assignment_id)).filter(user__in=signup_student).values('user')        
        
        submitted = Submit.objects.filter(assignment=Assignment.objects.get(id=assignment_id)).filter(user__in=submitted_users)
        not_submitted = User.objects.filter(~Q(id__in=submitted_users) & Q(id__in=signup_student))
            
        return render(request, self.template_name, {
            'submitted' : submitted,
            'not_submitted' : not_submitted
        })
        
class ProfessorAssignmentAddView(ProfessorMixin, FormView):
    template_name = 'judge/professor/professor_assignment_add.html'
    form_class = AssignmentAddForm

    def post(self, request, *args, **kwargs):
        self.generate_assignment(self.request)
            
        return redirect(reverse_lazy('judge:professor_assignment_list'))
     

    def generate_assignment(self, request):
        #--- Creating assignment directory 
        temp_path = os.path.join(os.path.join(os.path.expanduser('~'), 'assignment_cache'), request.user.username + "_temp")
        if not os.path.exists(temp_path):
            os.mkdir(temp_path)
        
        origin_path = os.getcwd()
        os.chdir(temp_path)
        
        print(origin_path)
        
        
        #--- upload files
        origin_file_name = ['assignment_out_file', 'assignment_in_file']
        uploaded_file_name = ['out', 'in']        
        
        checkedNoFile = request.POST.get('assignment_no_in_file') == "on"
        endOfSeq = 1 if checkedNoFile else 2
            
        for seq in range(0, endOfSeq):
            with open(uploaded_file_name[seq], 'wb+') as dest:
                for chunk in request.FILES[origin_file_name[seq]].chunks():
                    dest.write(chunk)                    
                    
        #--- separate files
        #--- It can't prevent integrity each file
        
        # inner def
        def file_to_zip(file, myzip, file_list, postFix):
            buf = None
            cnt = 1
            lines = file.readlines()
            
            try:
                if lines[-1].rstrip() is not None:
                    lines.append("")
            except IndexError:
                return 0    # when the file is empty
            
            for line in lines:
                line = line.rstrip()
                
                if not line:
                    file_elem_name = str(cnt) + "." + postFix
                    with open(file_elem_name, "w") as file_elem:
                        file_elem.write(buf)
                    
                    myzip.write(file_elem_name)
                    file_list.append(file_elem_name)
                    
                    buf = None
                    cnt = cnt + 1
                else:
                    if not buf:
                        buf = line
                    else:
                        buf = buf + "\n" + line
            
            return cnt - 1
            
        
        in_cnt = 1  
        out_cnt = 1 # temp value
    
        
        with zipfile.ZipFile("problem.zip", "w") as myzip:
            file_list = ["in", "out", "problem.zip"]
            
            with open("out", "r") as out_file:
                out_cnt = file_to_zip(out_file, myzip, file_list, "out")
            
            if checkedNoFile:
                file_list.remove("in")
            else:
                with open("in", "r") as in_file:
                    in_cnt = file_to_zip(in_file, myzip, file_list, "in")
        
        #--- insert to database
        if in_cnt == out_cnt and out_cnt > 0:
            assignment_instance = Assignment()    
            assignment_instance.name = request.POST.get('assignment_name')
            assignment_instance.desc = request.POST.get('assignment_desc')
            assignment_instance.deadline = timezone.make_aware(datetime.datetime.now() + datetime.timedelta(days=int(request.POST.get('assignment_deadline'))))
            assignment_instance.max_score = out_cnt #It will be changed
            assignment_instance.subject = Subject.objects.get(id=int(request.session.get('subject_id')))
            assignment_instance.problem_upload("problem.zip")
            assignment_instance.no_input_file = checkedNoFile
            assignment_instance.delay_submission = request.POST.get('assignment_delayed_submission') == 'on'
            assignment_instance.save()
        else:
            print(in_cnt, out_cnt)
            raise forms.ValidationError("input set and output set are not corresponded..")

        #--- remove files
        for f in file_list:
            os.remove(f)
        os.chdir(origin_path)
        os.rmdir(temp_path)
        
class ProfessorAssignmentUpdateView(ProfessorMixin, FormView):
    template_name = 'judge/professor/professor_assignment_update.html'
    form_class = AssignmentUpdateForm
        
    def get(self, request, * args, **kwargs):
        assignment_id = request.GET.get('assignment_id')
        request.session['assignment_id'] = assignment_id
        return render(request, self.template_name, {'form' : self.form_class, 'assignment' : Assignment.objects.get(id=assignment_id)})   # + current assignment object

    def post(self, request, * args, **kwargs):
        assignment_instance = Assignment.objects.get(id=request.session.get('assignment_id'))
        assignment_instance.name = request.POST.get('assignment_name')
        assignment_instance.desc = request.POST.get('assignment_desc')
        assignment_deadline = request.POST.get('assignment_deadline')
        if assignment_deadline is not '':
            assignment_instance.deadline = timezone.make_aware(datetime.datetime.now() + datetime.timedelta(days=int(assignment_deadline)))
        assignment_instance.save()
        return redirect(reverse_lazy('judge:professor_assignment_list'))

class ProfessorAssignmentDeleteView(ProfessorMixin, TemplateView):
    template_name = 'judge/professor/professor_assignment_delete.html'

class ProfessorAssignmentStudentCodeView(ProfessorMixin, TemplateView):
    template_name = "judge/common/common_assignment_student_code.html"
    
    def get(self, request, *args, **kwargs):
        submit_id = request.GET.get("submit_id")
        submit = Submit.objects.get(id=int(submit_id))
        
        subject_id = int(request.session.get('subject_id'))
        language = Subject.objects.get(id=subject_id).language
        
        codingForm = CodingForm(mode=language.mode, template=submit.code)
        
        return render(request, self.template_name,
                      {"submit" : submit,
                       "codingForm" : codingForm })
        


# Student area------------------------------------------------------------------------------------------------------------------------
class StudentSubjectLV(StudentMixin, ListView):
    template_name = 'judge/student/student_subject_list.html'
    
    @classmethod
    def get(self, request, *args, **kwargs):
        signup_class = Signup_class_student.objects.filter(user_id=request.user.id)
        
        signup_class_available = signup_class.filter(state=Signup_class_base.State.Accepted)
        signup_class_waiting = signup_class.filter(state=Signup_class_base.State.Waiting) 
        
        return render(request, self.template_name, 
                      { 'signup_class_available' : signup_class_available,
                       'signup_class_waiting' : signup_class_waiting})
    
    def post(self, request, *args, **kwargs):
        form = request.POST
        
        if "accept" in form.keys():
            print("accept key exist")
        elif "hided" in form.keys():
            subject = Subject.objects.get(id=int(request.POST.get('subject_id')))
            subject.hided = True;
            subject.save()
        
        return self.get(request)
    
class StudentSubjectAddView(StudentMixin, FormView):    
    template_name = 'judge/student/student_subject_add.html'
    form_class = StudentSubjectAddForm
    
    def get(self, request, * args, **kwargs):
        q = ~Q(state=Signup_class_base.State.Owned)
        participated_student_list = Signup_class_student.objects.filter(user=request.user.id).filter(q).order_by('state')
        
        return render(request, self.template_name, 
                      {'participated_student_list': participated_student_list,
                      'form': self.form_class
                      })
        
    def post(self, request, * args, **kwargs):
        subject = None
        subject_id = request.POST.get('subject_id')
        access_code = request.POST.get('access_code')
        
        try:
            subject = Subject.objects.get(id=subject_id)
            if subject.access_code == access_code:
                Signup_class_student.objects.create(
                    subject = subject,
                    user = request.user,
                    state = Signup_class_base.State.Waiting
                )
                messages.info(request, "Request was sent successfully!")
            else:
                messages.info(request, "access code is invalid!")    
        except Subject.DoesNotExist:
            messages.info(request, "Subject_id is invalid!")
        except IntegrityError:
            messages.info(request, "This subject already requested..")
        
        return self.get(request)

class StudentAssignmentLV(StudentMixin, ListView):
    template_name = 'judge/student/student_assignment_list.html'
    paginate_by = 10
    
    def post(self, request, *args, **kwargs):
        subject_id = request.POST.get('subject_id')
        request.session['subject_id'] = subject_id
        
        return self.get(request, args, kwargs)

    def get(self, request, *args, **kwargs):
        if('subject_id' not in request.session):
            return redirect(reverse_lazy('judge:student_subject_list'))
        
        subject_id = request.session.get('subject_id')
        assignment = Assignment.objects.filter(subject_id = subject_id)
        subject = Subject.objects.get(id = subject_id)
        
        for a in assignment:
            try:
                a.submit = Submit.objects.filter(assignment=a).get(user=request.user)
            except Submit.DoesNotExist:
                pass
            
        cur_time = timezone.make_aware(datetime.datetime.now())
        for a in assignment:
            a.can_solve = True if a.deadline > cur_time or a.delay_submission else False 
        
        return render(request, self.template_name,
                       { 'assignment' : assignment, 'subject' : subject })

class StudentAssignment(StudentMixin, FormView):
    template_name = 'judge/student/student_assignment.html'
    form_class = CodingForm(mode='c_cpp', template='#It is not general way')
    #we need to change mode by language in get or post(maybe get)
    #Is form_class variable necessary?
    
    def get(self, request, * args, **kwargs):
        assignment_id = request.GET.get('assignment_id')
        
        if not assignment_id:
            assignment_id = request.session.get('assignment_id')
        else:
           request.session['assignment_id'] = assignment_id
        
        assignment = Assignment.objects.get(id=assignment_id)
        language = Language.objects.get(lang_id=Subject.objects.get(id=request.session.get('subject_id')).language_id)
        coding_form = CodingForm(mode=language.mode, template=language.template)
        
        try:
            submit = Submit.objects.filter(assignment=assignment).get(user=request.user)
            coding_form = CodingForm(mode=language.mode, template=submit.code)
        except Submit.DoesNotExist:
            pass
        
        # If get page with result
        if 'judge_result' in kwargs.keys():
            judge_result = kwargs.pop('judge_result')
            return render(request, self.template_name,
                       {'form' : CodingForm(mode=language.mode, template=judge_result['last_code']),
                         'assignment' : assignment,
                         'lang' : language,
                         'result' : judge_result['result'],
                         'submit_instance' : judge_result['submit_instance']})
        
        # basic get
        return render(request, self.template_name,
                       {'form' : coding_form,
                         'assignment' : assignment,
                         'lang' : language})

    def post(self, request, * args, **kwargs):
        if "judge" in request.POST.keys():
            context = dict()
            code = request.POST.get('code')
        
            assignment = Assignment.objects.get(id=request.session.get('assignment_id'))
            language = Language.objects.get(lang_id=Subject.objects.get(id=request.session.get('subject_id')).language_id)
            base_dir_path = os.path.join(os.path.join(os.path.expanduser('~'), 'assignment_cache'), str(assignment.id))
        
            if not os.path.exists(base_dir_path):
                self.create_structure(base_dir_path, assignment)
        
            self.create_src_file(code, os.path.join(base_dir_path, "students"),assignment, language, request)
        
            submit_instance = self.judge_student_src_file(code, base_dir_path, assignment, language, request, context)
        
            context['submit_instance'] = submit_instance
            context['last_code'] = code
            
            request.session['submit_instance'] = submit_instance
        
            return self.get(request, judge_result=context)    
        
        elif "submit" in request.POST.keys():
            if 'submit_instance' in request.session:
                self.submit_judge_result(request.session.pop('submit_instance'))
            return redirect(reverse_lazy('judge:student_assignment_list'))
        else:
            print("is not valid way!")
            return self.get(request)
        
    def create_structure(self, base_dir_path, assignment):
        origin_path = os.getcwd()
        
        os.mkdir(base_dir_path)
        os.chdir(base_dir_path)
        
        for dirs in ["problem", "students"]:
            os.mkdir(dirs)
        
        #--- generate init and problem.zip file
        with open(os.path.join("problem", "init.yml"), "w") as init_file:
            init_file.write("archive: problem.zip\ntest_cases:")
            
            if assignment.no_input_file:
                init_file.write("\n- {out: 1.out, points: 1}")
            else:
                for i in range(1, assignment.max_score + 1):
                    init_file.write("\n- {" + "in: {0}.in, out: {0}.out, points: 1".format(i) + "}")

        assignment.problem_download(os.path.join("problem", "problem.zip"))
        
        #--- generate config file
        config_file = open("config.yml", "w")
        base_config_file = open(os.path.join(os.path.join(os.path.expanduser('~'), "settings"), "base_config.yml"), "r")
        
        config_file.write("problem_storage_root:\n  -  {0}\n".format(base_dir_path))

        while True:
            line = base_config_file.readline()
            if not line:
                break
            config_file.write(line)
            
        config_file.close()
        base_config_file.close()
        
        os.chdir(origin_path)

    
    def create_src_file(self, code, student_dir_path, assignment, language, request):        
        src_path = os.path.join(student_dir_path, request.user.username + "." + language.extension)
        
        src_file = open(src_path, "w")
        src_file.write(code)
        src_file.close()
        
    def judge_student_src_file(self, code, base_dir_path, assignment, language, request, context):
        now = datetime.datetime.now()
        judge_time = timezone.make_aware(now)
        judge_time_stamp = now.timestamp()
        
        config_file_path = os.path.join(base_dir_path, "config.yml")
        init_file_path = os.path.join(os.path.join(base_dir_path, "problem"), "init.yml")
        
        student_file_path = os.path.join(base_dir_path, "students")
        student_file_path = os.path.join(student_file_path, request.user.username + "." + language.extension)
        
        points = []
        with open(init_file_path, 'r') as stream:
            try:
                prob_info = yaml.safe_load(stream)
                tc = prob_info['test_cases']
                for t in tc:
                    points.append(t['points'])
            except yaml.YAMLError as exc:
                print(exc)

        max_score = sum(points)
        # Make parsed result of dmoj-judge
        a = subprocess.check_output(["dmoj-cli", "-c", config_file_path, "-e", language.lang_id, "submit", "problem", language.lang_id, student_file_path ])
        sp = [s.decode("utf-8") for s in a.split()] #convert byte to string

        i = 0
        total_get = 0
        result_output = "\n".join(a.decode("utf-8").split("\n")[6:-3])
        result_html = Ansi2HTMLConverter().convert(result_output)
        bs = BeautifulSoup(result_html,'html.parser')
        context['result'] = str(bs.find('pre'))
        
        ac_ansi = '\x1b[1m\x1b[32mAC\x1b[0m'
        
        while True:
            if sp[i] == "Done":
                break
            if sp[i] == "Test":
                if sp[i+3] == ac_ansi:
                    total_get = total_get + points[int(sp[i + 2]) - 1]

            i = i + 1
    
        # return submit_instance
        submit_instance = dict()
        submit_instance['score'] = total_get
        submit_instance['user_id'] = request.user.id
        submit_instance['assignment_id'] = assignment.id
        submit_instance['code'] = code
        submit_instance['judge_time_stamp'] = judge_time_stamp
        submit_instance['ontime'] = judge_time <= assignment.deadline

        return submit_instance
    
    def submit_judge_result(self, submit_instance):
        submit_base = None
        try:
            submit_base = Submit.objects.filter(assignment_id = submit_instance.get('assignment_id')).get(user_id=submit_instance.get('user_id'))
        except Submit.DoesNotExist:
            submit_base = Submit()
        
        submit_base.submit_ontime = submit_instance['ontime']
        submit_base.score = submit_instance['score']
        submit_base.submit_time = timezone.make_aware(datetime.datetime.fromtimestamp(submit_instance['judge_time_stamp']))
        submit_base.code = submit_instance['code']
        submit_base.assignment = Assignment.objects.get(id=submit_instance['assignment_id'])
        submit_base.user = User.objects.get(id=submit_instance['user_id'])
        submit_base.save()

class StudentAssignmentStudentCodeView(StudentMixin, TemplateView):
    template_name = "judge/common/common_assignment_student_code.html"
    
    def get(self, request, *args, **kwargs):
        submit_id = request.GET.get("submit_id")
        submit = Submit.objects.get(id=int(submit_id))
        
        subject_id = int(request.session.get('subject_id'))
        language = Subject.objects.get(id=subject_id).language
        
        codingForm = CodingForm(mode=language.mode, template=submit.code)
        
        return render(request, self.template_name,
                      {"submit" : submit,
                       "codingForm" : codingForm })
        