from django import forms
from tasks.models import TodoItem


class AddTaskForm(forms.Form):
	description = forms.CharField(max_length=64, label='')

class TodoItemForm(forms.ModelForm):
	class Meta:
		model = TodoItem
		fields = ('description','priority','tags', 'trello_sync')
		labels = {'description': 'Описание', 'priority': 'Приоритет', 'tags':'тэги', 'trello_sync':'Синхронизировать с Trello'}

class TodoItemExportForm(forms.Form):
	prio_high = forms.BooleanField(
		label='высокая важность', initial=True, required=False
		)
	prio_med = forms.BooleanField(
		label='средней важности', initial=True, required=False
		)
	prio_low = forms.BooleanField(
		label='низкой важности', initial=False, required=False
		)
	prio_sorted = forms.BooleanField(
		label='Разбить по приоритетам', initial=False, required=False
		)

class TrelloImportForm(forms.Form):
	board_id = forms.CharField(max_length=24, label='')

# class TrelloSyncForm(forms.Form):
# 	trello_sync = forms.BooleanField(label='Синхронизировать с Trello', initial=False, required=False)