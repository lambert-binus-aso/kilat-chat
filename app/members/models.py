from django.db import models

""" MASTER TABLE """

class User(models.Model):
    username = models.CharField(max_length=30)
    email = models.CharField(max_length=128, unique=True)

class AI_Models(models.Model):
    name = models.CharField(max_length=128)
    provider = models.CharField(max_length=128)
    cost_per_mil_input_toks = models.DecimalField() # consider using DecimalField
    cost_per_mil_output_toks = models.DecimalField() # consider using DecimalField


""" TRANSACTION TABLE """


class Conversations(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )
    title = models.CharField(max_length=30)
    created_at = models.DateTimeField(auto_now_add=True)
    
class Messages(models.Model):
    conversation = models.ForeignKey(
        Conversations,
        on_delete=models.CASCADE # CASCADE deletes object containing the foreign key as well
    )
    sent_at = models.DateTimeField(auto_now_add=True)
    model = models.ForeignKey(
        AI_Models,
        on_delete=models.PROTECT
    )
    raw_msg = models.TextField()

class Responses(models.Model):
    message = models.OneToOneField(
        Messages,
        on_delete=models.CASCADE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    raw_output = models.TextField()

class APIUsage(models.Model):
    message = models.OneToOneField(
        Messages,
        on_delete=models.CASCADE,
    )
    input_tokens = models.PositiveIntegerField()    
    output_tokens = models.PositiveIntegerField()
    total_cost = models.DecimalField(
        max_digits=18,
        decimal_places=10
    ) # in USD