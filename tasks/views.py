from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import ListView
from django.views.generic.detail import DetailView
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Q
from django.core.mail import send_mail
from django.conf import settings

from tasks.models import TodoItem
from tasks.forms import AddTaskForm, TodoItemForm, TodoItemExportForm

from datetime import datetime as dt, timezone

@login_required
def index(request):
	return HttpResponse('Примитивный ответ из приложения tasks')

# def tasks_list(request):
# 	all_tasks = TodoItem.objects.all()
# 	return render(
# 		request,
# 		'tasks/list.html',
# 		{'tasks': all_tasks}
# 	)

def complete_task(request, uid):
	t = TodoItem.objects.get(id=uid)
	t.is_completed = True
	t.save()
	return HttpResponse('OK')

def add_task(request):
	if request.method == 'POST':
		desc = request.POST['description']
		t = TodoItem(description=desc)
		t.save()
	return reverse('tasks:list')

def delete_task(request, uid):
	t = TodoItem.objects.get(id=uid)
	t.delete()
	messages.success(request, 'Задача  удалена')
	return redirect(reverse('tasks:list'))

# def task_create(request):
# 	if request.method == 'POST':
# 		form = TodoItemForm(request.POST)
# 		if form.is_valid():
# 			form.save()
# 			return redirect('/tasks/list')
# 	else:
# 		form = TodoItemForm()
# 	return render(request, 'tasks/create.html', {'form': form})

class TaskListView(LoginRequiredMixin,ListView):
	model = TodoItem
	context_object_name = 'tasks'
	template_name = 'tasks/list.html'
	
		
	def get_queryset(self):
		# qs = super().get_queryset()
		now = dt.now()
		u = self.request.user
		'''
		поскольку мы импортировали и отнаследовали обработчик от класса LoginRequiredMixin, то проверять пользователя
		на то, залогинен ли он нет необходимости

		if u.is_anonymous:
			return []
		'''
		return u.tasks.all()
	
class UncompletedTaskListView(LoginRequiredMixin, ListView):
	model = TodoItem
	context_object_name = 'tasks'
	template_name = 'tasks/uncompleted_tasks.html'

	def get_queryset(self):
		u = self.request.user
		return TodoItem.objects.filter(owner=u).filter(is_completed=False)

def SortedTaskListView(request):
	u = request.user
	template = 'tasks/sorted_tasks.html'
	tasks = TodoItem.objects.filter(owner=u)
	high_in_func = tasks.filter(priority=1)
	med = tasks.filter(priority=2)
	low = tasks.filter(priority=3)
	return render(request, template, {'high_in_template': high_in_func, 'med': med, 'low': low})

class TimeOfDay(LoginRequiredMixin, ListView):
	model = TodoItem
	context_object_name = 'tasks'
	template_name = 'tasks/time_of_day.html'

	def get_context_data(self, **kwargs):
		# string = 'day'
		now = dt.now()
		if now.hour in range(6):
			time_of_day = 'night'
			time_of_day_ru = 'ночь'
		elif now.hour in range(6,12):
			time_of_day = 'morning'
			time_of_day_ru = 'утро'
		elif now.hour in range(12,18):
			time_of_day = 'day'
			time_of_day_ru = 'день'
		elif now.hour in range(18,24):
			time_of_day = 'evening'
			time_of_day_ru = 'вечер'

		context = super().get_context_data(**kwargs)
		context['time_of_day'] = time_of_day
		context['time_of_day_ru'] = time_of_day_ru
		return context


class TaskCreateView(View):
	def my_render(self, request, form):
		return render(request, 'tasks/create.html', {'form': form})

	def post(self, request, *args, **kwargs):
		form = TodoItemForm(request.POST)
		if form.is_valid():
			new_task = form.save(commit=False)
			new_task.owner = request.user
			new_task.save()
			messages.success(request, 'Задача создана')
			return redirect(reverse('tasks:list'))
			
		return self.my_render(request, form)

	def get(self, request, *args, **kwargs):
		form = TodoItemForm()
		return self.my_render(request, form)

class TaskEditView(LoginRequiredMixin, View):
	def post (self, request, pk, *args, **kwargs):
		t = TodoItem.objects.get(id=pk)
		form = TodoItemForm(request.POST, instance=t)
		if form.is_valid():
			new_task = form.save(commit=False)
			new_task.owner = request.user
			new_task.save()
			messages.success(request, 'Задача изменена')
			return redirect(reverse('tasks:list'))
		return render(request, 'tasks/edit.html', {'form':form, 'task':t })
	def get(self, request, pk, *args, **kwargs):
		t = TodoItem.objects.get(id=pk)
		form = TodoItemForm(instance=t)
		return render(request, 'tasks/edit.html', {'form': form, 'task': t})

class TaskDetailsView(DetailView):
	model = TodoItem
	template_name = 'tasks/details.html'

class TaskExportView(LoginRequiredMixin, View):
	def generate_body(self, user, priorities):
		q = Q()
		if priorities['prio_high']:
			q = q | Q(priority=TodoItem.PRIORITY_HIGH)
		if priorities['prio_med']:
			q = q | Q(priority=TodoItem.PRIORITY_MEDIUM)
		if priorities['prio_low']:
			q = q | Q(priority=TodoItem.PRIORITY_LOW)
		tasks = TodoItem.objects.filter(owner=user).filter(q).all()

		high_pri, med_pri, low_pri = [],[],[]
		
		body = 'Ваши задачи и приоритеты:\n'
		if priorities['prio_sorted']:
			body += '(Разбито по приоритетам):\n'
			for t in list(tasks):
				if t.priority == 1:
					high_pri.append(t)
				elif t.priority == 2:
					med_pri.append(t)
				else:
					low_pri.append(t)
			body += '\nВысокий приоритет\n'
			for t in high_pri:
				if t.is_completed:
					body += f"[x] {t.description} \n"
				else:
					body += f"[ ] {t.description} \n"
			body += '__________________________________________________________'
			body += '\nСредний приоритет\n'
			for t in med_pri:
				if t.is_completed:
					body += f"[x] {t.description} \n"
				else:
					body += f"[ ] {t.description} \n"
			body += '__________________________________________________________'
			body += '\nНизкий приоритет\n'
			for t in low_pri:
				if t.is_completed:
					body += f"[x] {t.description} \n"
				else:
					body += f"[ ] {t.description} \n"
			
		else:
			for t in list(tasks):
				if t.is_completed:
					body += f"[x] {t.description} ({t.get_priority_display()})\n"
				else:
					body += f"[ ] {t.description} ({t.get_priority_display()})\n"
		return body

	def post(self, request, *args, **kwargs):
		form = TodoItemExportForm(request.POST)
		if form.is_valid():
			email = request.user.email
			body = self.generate_body(request.user, form.cleaned_data)
			send_mail('Задачи', body, settings.EMAIL_HOST_USER, [email])
			messages.success(
				request, "Задачи были отправлены на почту %s" % email
				)
		else:
			messages.error(request, 'Что-то пошло не так, попробуйте еще раз')
		return redirect(reverse('tasks:list'))

	def get(self, request, *args, **kwargs):
		form = TodoItemExportForm()
		return render(request, 'tasks/export.html', {'form': form})