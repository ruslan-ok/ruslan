from django.contrib.auth.models import User
from django.db import models


class PirTable(models.Model):
  name   = models.CharField(u'Таблица', max_length = 200, blank = False)
  def __str__(self):
    return unicode(self.name)


class PirPart(models.Model):
  table = models.ForeignKey(PirTable, on_delete=models.CASCADE)
  name  = models.CharField(u'Блок данных', max_length = 200, blank = False)
  def __str__(self):
    return unicode(self.table.name) + u' / ' + unicode(self.rec)


class PirData(models.Model):
  table = models.ForeignKey(PirTable, on_delete=models.CASCADE)
  part = models.ForeignKey(PirPart, on_delete=models.CASCADE, default = 1)
  rec  = models.CharField(u'Запись таблицы', max_length = 1000, blank = False)
  def __str__(self):
    return unicode(self.part.table.name) + u' / ' + unicode(self.part.name) + u' / ' + unicode(self.rec)