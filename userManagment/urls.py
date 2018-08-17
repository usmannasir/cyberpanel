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

    url(r'^createNewACL$',views.createNewACL,name="createNewACL"),
    url(r'^createACLFunc$',views.createACLFunc,name="createACLFunc"),
    url(r'^deleteACL$',views.deleteACL,name="deleteACL"),
    url(r'^deleteACLFunc$',views.deleteACLFunc,name="deleteACLFunc"),
    url(r'^modifyACL$',views.modifyACL,name="modifyACL"),
    url(r'^fetchACLDetails$',views.fetchACLDetails,name="fetchACLDetails"),
    url(r'^submitACLModifications$',views.submitACLModifications,name="submitACLModifications"),
    url(r'^changeUserACL$',views.changeUserACL,name="changeUserACL"),
    url(r'^changeACLFunc$',views.changeACLFunc,name="changeACLFunc"),
    url(r'^resellerCenter$',views.resellerCenter,name="resellerCenter"),
    url(r'^saveResellerChanges$',views.saveResellerChanges,name="saveResellerChanges"),
]