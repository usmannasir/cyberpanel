// Wait for Angular to be ready
angular.element(document).ready(function() {
    // Ensure the CyberCP module exists
    if (typeof angular.module('CyberCP') === 'undefined') {
        console.error('CyberCP module not found!');
        return;
    }
    
    // Bootstrap Angular manually if needed
    var element = document.querySelector('[ng-controller="ListDockersitecontainer"]');
    if (element && !angular.element(element).data('$scope')) {
        console.log('Manually bootstrapping Angular for Docker container page');
        angular.bootstrap(element, ['CyberCP']);
    }
});