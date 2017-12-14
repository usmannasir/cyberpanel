#!/usr/bin/perl -w
use strict;
use CGI qw(:standard escapeHTML);

#get parameter

my $id = param('textfield');
my $hidden = param('hiddenField');
my $passwd = param('textfield2');
my $suggest = param('textfield3');
my $radio = param('radiobutton');
my $select = param('select');
# my $file = param('uploadfile');

print header(), start_html("Test post back"),
	p("id = ", tt(escapeHTML($id))),
	p("passwd = ", tt(escapeHTML($passwd))),
	p("hidden = ", tt(escapeHTML($hidden))),
	p("suggest = ", tt(escapeHTML($suggest))),
	p("radio = ", tt(escapeHTML($radio))),
	p("select = ", tt(escapeHTML($select))),
#	p("file = ", tt(escapeHTML($file))),
	end_html();
