(function(window, angular, $) {
    "use strict";
    angular.module('FileManagerApp')
	.controller('FileManagerFooterCtrl', [
    '$scope', '$rootScope', '$http', 'fileManagerConfig',   
    function($scope, $rootScope, $http, fileManagerConfig) {

        $scope.initialized = function() {
        	return fileManagerConfig.stats && fileManagerConfig.stats['timestamp'];
        };
                
        $scope.usedSpaceInfo = function() {
        	var s = fileManagerConfig.stats;
        	if (!s) return 'consumed: ?';
        	return "consumed: " +
			    s.value_used_total + " of " + 
				s.value_needed;
        };
        
        $scope.suppliersInfo = function() {
        	var s = fileManagerConfig.stats;
        	if (!s) return 'suppliers: ?';
        	return "suppliers: " + 
        		s.suppliers + " of " +
				s.max_suppliers + ", " + 
				s.online_suppliers + " online";
        };

        $scope.donatedSpaceInfo = function() {
        	var s = fileManagerConfig.stats;
        	if (!s) return 'donated: ?';
        	return "donated: " +
        		s.value_donated; 
        };

        $scope.customersInfo = function() {
        	var s = fileManagerConfig.stats;
        	if (!s) return 'customers: ?';
        	return "customers: " + 
        		s.customers;
        };
        
    }]);
})(window, angular, jQuery);
        