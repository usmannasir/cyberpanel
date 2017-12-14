from django.conf.urls import url
import views

urlpatterns = [

    url(r'^$', views.loadUserHome, name='loadUsersHome'),
    url(r'^viewProfile', views.viewProfile, name='viewProfile'),
    url(r'^createUser', views.createUser, name='createUser'),


    url(r'^submitUserCreation', views.submitUserCreation, name='submitUserCreation'),
    url(r'^modifyUsers',views.modifyUsers,name="modifyUsers"),
    url(r'^fetchUserDetails',views.fetchUserDetails,name="fetchUserDetails"),
    url(r'^saveModifications',views.saveModifications,name="saveModifications"),


    url(r'^deleteUser',views.deleteUser,name="deleteUser"),
    url(r'^submitUserDeletion',views.submitUserDeletion,name="submitUserDeletion"),
]