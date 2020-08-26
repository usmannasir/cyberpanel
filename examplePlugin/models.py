from django.db import models


class ExamplePlugin(models.Model):
    name = models.CharField(unique=True, max_length=255)

    class Meta:
        # db_table = "ExamplePlugin"
        pass
