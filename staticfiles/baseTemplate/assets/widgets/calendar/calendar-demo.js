$(document).ready(function() {

    $('#calendar-example-1').fullCalendar({
        header: {
            left: 'prev,next today',
            center: 'title',
            right: 'month,agendaWeek,agendaDay'
        },
        defaultDate: '2014-01-12',
        editable: true,
        events: [{
            title: 'All Day Event',
            start: '2014-01-01'
        }, {
            title: 'Long Event',
            start: '2014-01-07',
            end: '2014-01-10'
        }, {
            id: 999,
            title: 'Repeating Event',
            start: '2014-01-09T16:00:00'
        }, {
            id: 999,
            title: 'Repeating Event',
            start: '2014-01-16T16:00:00'
        }, {
            title: 'Meeting',
            start: '2014-01-12T10:30:00',
            end: '2014-01-12T12:30:00'
        }, {
            title: 'Lunch',
            start: '2014-01-12T12:00:00'
        }, {
            title: 'Birthday Party',
            start: '2014-01-13T07:00:00'
        }, {
            title: 'Click for Google',
            url: 'http://google.com/',
            start: '2014-01-28'
        }]
    });

    /* initialize the external events
		-----------------------------------------------------------------*/

    $('#external-events div.external-event').each(function() {

        // create an Event Object (http://arshaw.com/fullcalendar/docs/event_data/Event_Object/)
        // it doesn't need to have a start or end
        var eventObject = {
            title: $.trim($(this).text()) // use the element's text as the event title
        };

        // store the Event Object in the DOM element so we can get to it later
        $(this).data('eventObject', eventObject);

        // make the event draggable using jQuery UI
        $(this).draggable({
            zIndex: 999,
            revert: true, // will cause the event to go back to its
            revertDuration: 0 //  original position after the drag
        });

    });


    /* initialize the calendar
		-----------------------------------------------------------------*/

    $('#calendar-example-2').fullCalendar({
        header: {
            left: 'prev,next today',
            center: 'title',
            right: 'month,agendaWeek,agendaDay'
        },
        editable: true,
        droppable: true, // this allows things to be dropped onto the calendar !!!
        drop: function(date) { // this function is called when something is dropped

            // retrieve the dropped element's stored Event Object
            var originalEventObject = $(this).data('eventObject');

            // we need to copy it, so that multiple events don't have a reference to the same object
            var copiedEventObject = $.extend({}, originalEventObject);

            // assign it the date that was reported
            copiedEventObject.start = date;

            // render the event on the calendar
            // the last `true` argument determines if the event "sticks" (http://arshaw.com/fullcalendar/docs/event_rendering/renderEvent/)
            $('#calendar-example-2').fullCalendar('renderEvent', copiedEventObject, true);

            // is the "remove after drop" checkbox checked?
            if ($('#drop-remove').is(':checked')) {
                // if so, remove the element from the "Draggable Events" list
                $(this).remove();
            }

        }
    });

});
