<?php
$root = $argv[1] . '/admin/html/lib/LSWebAdmin/';
require $root . 'Config/Validation/PostTableValidationRuleInterface.php';
require $root . 'Config/Validation/ThrottlePostTableValidationRule.php';
require $root . 'Config/Service/ConfigActionService.php';
function verify($condition, $message) { if (!$condition) throw new RuntimeException($message); }
class ExtractedConfig {
    public $values, $errors = [];
    function __construct($values) {$this->values = $values;}
    function GetChildVal($key) {return $this->values[$key] ?? null;}
    function SetChildErr($key, $value) {$this->errors[$key] = $value;}
}
$rule = new LSWebAdmin\Config\Validation\ThrottlePostTableValidationRule();
foreach ([[300,86400,1],[86400,300,-1],[300,300,1]] as [$window,$backoff,$expected]) {
 $data = new ExtractedConfig(['throttleBlockWindow'=>$window,'throttleMaxBackoff'=>$backoff]);
 verify($rule->Validate(null,$data)===$expected,'cross-field validation changed');
 verify(($expected===-1) === isset($data->errors['throttleBlockWindow']),'validation error was not preserved');
 verify($data->values===['throttleBlockWindow'=>$window,'throttleMaxBackoff'=>$backoff],'values changed');
}
$method = new ReflectionMethod(LSWebAdmin\Config\Service\ConfigActionService::class,'resolveNoRestartFieldsForTable');
$method->setAccessible(true);
$fields=$method->invoke(null,'ADM_THROTTLE');
verify(array_keys($fields)===['throttleenabled','throttlemaxfailures','throttleblockwindow','throttlemaxbackoff','loginhistoryretention','opsauditretainfiles'],'save handling changed');
verify($method->invoke(null,'UNKNOWN')===[],'unknown table handling changed');
echo "PASS: actual bundled PHP cross-field checks (valid/equal/invalid), value preservation, and no-restart save field mapping\n";
