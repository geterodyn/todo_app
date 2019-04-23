from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
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
from taggit.models import Tag

from datetime import datetime as dt, timedelta
from trello import TrelloClient

from tasks.models import TodoItem
from tasks.forms import AddTaskForm, TodoItemForm, TodoItemExportForm, TrelloImportForm

@login_required
def index(request):
	return HttpResponse('Примитивный ответ из приложения tasks')

def filter_tags(tags_by_task):
	res = []
	for i in tags_by_task:
		for j in i:
			res.append(j)
	return list(set(res))


def complete_task(request, uid):
	t = TodoItem.objects.get(id=uid)
	t.is_completed = True
	t.save()
	return HttpResponse('OK')

def complete_trello(request, uid):
	task_todoapp = TodoItem.objects.get(id=uid)
	
	user = request.user
	key = user.profile.trello_key
	secret = user.profile.trello_secret
	client = TrelloClient(api_key=key, api_secret=secret)
	board = client.list_boards()[0]		# захардкодил самую первую доску в Trello
	left_most = board.list_lists()[0]
	right_most = board.list_lists()[-1]
	for task in left_most.list_cards():
		if task.name == task_todoapp.description:
			task.change_list(right_most.id)
	
	task_todoapp.is_completed = True
	task_todoapp.save()
	return HttpResponse("OK")


# def add_task(request):
# 	if request.method == 'POST':
# 		desc = request.POST['description']
# 		t = TodoItem(description=desc)
# 		t.save()

# 	return reverse('tasks:list')

def delete_task(request, uid, tag_slug=None):
	t = TodoItem.objects.get(id=uid)
	t.delete()
	messages.success(request, 'Задача  удалена')
	return redirect(reverse('tasks:list_by_tag',args=tag_slug)) if tag_slug else redirect(reverse('tasks:list'))

# def task_create(request):
# 	if request.method == 'POST':
# 		form = TodoItemForm(request.POST)
# 		if form.is_valid():
# 			form.save()
# 			return redirect('/tasks/list')
# 	else:
# 		form = TodoItemForm()
# 	return render(request, 'tasks/create.html', {'form': form})

def SortedTaskListView(request):
	u = request.user
	template = 'tasks/sorted_tasks.html'
	tasks = TodoItem.objects.filter(owner=u)
	high = tasks.filter(priority=1)
	med = tasks.filter(priority=2)
	low = tasks.filter(priority=3)
	return render(request, template, {'high': high, 'med': med, 'low': low})

class TaskListView(LoginRequiredMixin,ListView):
	model = TodoItem
	context_object_name = 'tasks'
	template_name = 'tasks/list.html'

	def get_queryset(self):
		# qs = super().get_queryset()
		u = self.request.user
		'''
		поскольку мы импортировали и отнаследовали обработчик от класса LoginRequiredMixin, то проверять пользователя
		на то, залогинен ли он нет необходимости

		if u.is_anonymous:
			return []
		'''
		return u.tasks.all()

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		u = self.request.user

		user_tasks = self.get_queryset()
		tags = []
		for t in user_tasks:
			tags.append(list(t.tags.all()))
		
		context['tags'] = filter_tags(tags)
		return context


class UncompletedTaskListView(LoginRequiredMixin, ListView):
	model = TodoItem
	context_object_name = 'tasks'
	template_name = 'tasks/uncompleted_tasks.html'

	def get_queryset(self):
		u = self.request.user
		return TodoItem.objects.filter(owner=u).filter(is_completed=False)

class TaskCreateView(View):
	def my_render(self, request, form):
		return render(request, 'tasks/create.html', {'form': form})

	def post(self, request, *args, **kwargs):
		form = TodoItemForm(request.POST)
		if form.is_valid():
			new_task = form.save(commit=False)
			new_task.owner = request.user
			new_task.save()
			form.save_m2m()
			messages.success(request, 'Задача добавлена')
			if form.cleaned_data['trello_sync']:
				user = request.user
				key = user.profile.trello_key
				secret = user.profile.trello_secret
				client = TrelloClient(api_key=key, api_secret=secret)
				board = client.get_board(user.profile.trello_board)
				to_do = board.list_lists()[0]
				to_do.add_card(new_task.description)

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
			form.save_m2m()
			messages.success(request, 'Задача изменена')
			return redirect(reverse('tasks:list'))
		return render(request, 'tasks/edit.html', {'form':form, 'task':t })
	def get(self, request, pk, *args, **kwargs):
		t = TodoItem.objects.get(id=pk)
		form = TodoItemForm(instance=t)
		return render(request, 'tasks/edit.html', {'form': form, 'task': t})

class TrelloTaskImport(LoginRequiredMixin, View):
	def post(self,request,*args,**kwargs):
		form = TrelloImportForm(request.POST)
		user = request.user
		key = user.profile.trello_key
		secret = user.profile.trello_secret
		if form.is_valid():
			board_id = form.cleaned_data['board_id']
			client = TrelloClient(api_key=key, api_secret=secret)
			board = client.get_board(board_id)
			left_most = board.list_lists()[0]
			# right_most = board.list_lists()[-1]
			todo_tasks = left_most.list_cards()
			for task in todo_tasks:
				t = TodoItem(description=task.name)
				t.owner = user
				t.trello_id = task.id
				t.save()
			messages.success(request, 'Задачи успешно импортированы')
			return redirect(reverse('tasks:list'))
	def get(self,request,*args,**kwargs):
		form = TrelloImportForm()
		return render(request, 'tasks/import.html', {'form':form})





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

		body = 'Ваши задачи и приоритеты:\n'
		if priorities['prio_sorted']:
			body += '(Разбито по приоритетам):\n'
			
			high_pri = [t for t in tasks if t.priority == 1]
			med_pri = [t for t in tasks if t.priority == 2]
			low_pri = [t for t in tasks if t.priority == 3]
	
			body += '\nВысокий приоритет\n'
			for t in high_pri:
				if t.is_completed:
					body += f"[x] {t.description} (тэги задачи - {', '.join([tag.name for tag in t.tags.all()])})\n"
				else:
					body += f"[ ] {t.description} (тэги задачи - {', '.join([tag.name for tag in t.tags.all()])})\n"
			body += '__________________________________________________________'
			body += '\nСредний приоритет\n'
			for t in med_pri:
				if t.is_completed:
					body += f"[x] {t.description} (тэги задачи - {', '.join([tag.name for tag in t.tags.all()])})\n"
				else:
					body += f"[ ] {t.description} (тэги задачи - {', '.join([tag.name for tag in t.tags.all()])})\n"
			body += '__________________________________________________________'
			body += '\nНизкий приоритет\n'
			for t in low_pri:
				if t.is_completed:
					body += f"[x] {t.description} (тэги задачи - {', '.join([tag.name for tag in t.tags.all()])})\n"
				else:
					body += f"[ ] {t.description} (тэги задачи - {', '.join([tag.name for tag in t.tags.all()])})\n"
			
		else:
			for t in list(tasks):
				if t.is_completed:
					body += f"[x] {t.description} ({t.get_priority_display()}) (тэги задачи - {', '.join([tag.name for tag in t.tags.all()])})\n"
				else:
					body += f"[ ] {t.description} ({t.get_priority_display()}) (тэги задачи - {', '.join([tag.name for tag in t.tags.all()])})\n"
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

class TimeOfDay(LoginRequiredMixin, ListView):
	model = TodoItem
	context_object_name = 'tasks'
	template_name = 'tasks/time_of_day.html'

	def get_context_data(self, **kwargs):
		# string = 'day'
		now = dt.now() + timedelta(hours=7)
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

def tasks_by_tag(request, tag_slug=None):
    u = request.user
    tasks = TodoItem.objects.filter(owner=u).all()
    total_tasks_number = len(TodoItem.objects.filter(owner=u).all())
    completed_task_number = len(TodoItem.objects.filter(owner=u).filter(is_completed=True).all())

    tag = None
    if tag_slug:
        tag = get_object_or_404(Tag, slug=tag_slug)
        tasks = tasks.filter(tags__in=[tag])

    all_tags = [list(t.tags.all()) for t in tasks]
    completed_task = [t for t in tasks if t.is_completed == True]
    all_tags = filter_tags(all_tags)

    return render(
        request,
        "tasks/list_by_tag.html",
        {"tag": tag, "tasks": tasks, "all_tags": all_tags,
         "total": total_tasks_number, "completed": completed_task_number},
    )

