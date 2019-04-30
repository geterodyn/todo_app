from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver
from tasks.models import TagCount, PriorityCount, TodoItem
from taggit.models import Tag


@receiver(m2m_changed, sender=TodoItem.tags.through)
def task_tags_updated(sender, instance, action, model, **kwargs):
    if action != "post_add":
        return
    for tagname in instance.tags.names():
        tagmodel = model.objects.filter(name=tagname).first()
        obj, created = TagCount.objects.get_or_create(      # Если объект с такими параметрами уже есть, то created=False. 
                        tag_slug=tagmodel.slug,             # Если объект создаётся, то created=True
                        tag_name=tagmodel.name,
                        tag_id=tagmodel.id,
                        )
        count = tagmodel.taggit_taggeditem_items.count()
        obj.tag_count = count
        obj.save()

# @receiver(post_delete, sender=TodoItem)
# def task_tags_delete_updated(sender, instance, **kwargs):
#     for tagname in instance.tags.names():
#         tagmodel = Tag.objects.filter(name=tagname).first()
#         obj = TagCount.objects.get(tag_id=tagmodel.id)
#         obj.tag_count -= 1
#         obj.save()

@receiver(post_save, sender=TodoItem)
def task_priority_updated(sender, **kwargs):
    for prio in range(1,4):
        obj, created = PriorityCount.objects.get_or_create(prio_level=prio)
        count = TodoItem.objects.filter(priority=prio).count()
        obj.prio_count = count
        obj.save()