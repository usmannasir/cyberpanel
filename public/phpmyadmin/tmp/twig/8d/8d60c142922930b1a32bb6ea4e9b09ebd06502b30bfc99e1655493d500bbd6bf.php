<?php

use Twig\Environment;
use Twig\Error\LoaderError;
use Twig\Error\RuntimeError;
use Twig\Extension\SandboxExtension;
use Twig\Markup;
use Twig\Sandbox\SecurityError;
use Twig\Sandbox\SecurityNotAllowedTagError;
use Twig\Sandbox\SecurityNotAllowedFilterError;
use Twig\Sandbox\SecurityNotAllowedFunctionError;
use Twig\Source;
use Twig\Template;

/* scripts.twig */
class __TwigTemplate_ff0244f5f4df4c27dbf7c52d335f1dc0af6be0a0d9134bd0506c665f9a4b9e9b extends \Twig\Template
{
    private $source;
    private $macros = [];

    public function __construct(Environment $env)
    {
        parent::__construct($env);

        $this->source = $this->getSourceContext();

        $this->parent = false;

        $this->blocks = [
        ];
    }

    protected function doDisplay(array $context, array $blocks = [])
    {
        $macros = $this->macros;
        // line 1
        $context['_parent'] = $context;
        $context['_seq'] = twig_ensure_traversable(($context["files"] ?? null));
        foreach ($context['_seq'] as $context["_key"] => $context["file"]) {
            // line 2
            echo "  <script data-cfasync=\"false\" type=\"text/javascript\" src=\"";
            echo twig_escape_filter($this->env, ($context["base_dir"] ?? null), "html", null, true);
            echo "js/";
            // line 3
            echo twig_escape_filter($this->env, ((((is_string($__internal_compile_0 = twig_get_attribute($this->env, $this->source, $context["file"], "filename", [], "any", false, false, false, 3)) && is_string($__internal_compile_1 = "vendor/") && ('' === $__internal_compile_1 || 0 === strpos($__internal_compile_0, $__internal_compile_1))) || (is_string($__internal_compile_2 = twig_get_attribute($this->env, $this->source, $context["file"], "filename", [], "any", false, false, false, 3)) && is_string($__internal_compile_3 = "messages.php") && ('' === $__internal_compile_3 || 0 === strpos($__internal_compile_2, $__internal_compile_3))))) ? (twig_get_attribute($this->env, $this->source, $context["file"], "filename", [], "any", false, false, false, 3)) : (("dist/" . twig_get_attribute($this->env, $this->source, $context["file"], "filename", [], "any", false, false, false, 3)))), "html", null, true);
            // line 4
            ((twig_in_filter(".php", twig_get_attribute($this->env, $this->source, $context["file"], "filename", [], "any", false, false, false, 4))) ? (print (PhpMyAdmin\Url::getCommon(twig_array_merge(twig_get_attribute($this->env, $this->source, $context["file"], "params", [], "any", false, false, false, 4), ["v" => ($context["version"] ?? null)])))) : (print (twig_escape_filter($this->env, ("?v=" . twig_urlencode_filter(($context["version"] ?? null))), "html", null, true))));
            echo "\"></script>
";
        }
        $_parent = $context['_parent'];
        unset($context['_seq'], $context['_iterated'], $context['_key'], $context['file'], $context['_parent'], $context['loop']);
        $context = array_intersect_key($context, $_parent) + $_parent;
        // line 6
        echo "
<script data-cfasync=\"false\" type=\"text/javascript\">
// <![CDATA[
";
        // line 9
        echo ($context["code"] ?? null);
        echo "
";
        // line 10
        if ( !twig_test_empty(($context["files"] ?? null))) {
            // line 11
            echo "AJAX.scriptHandler
";
            // line 12
            $context['_parent'] = $context;
            $context['_seq'] = twig_ensure_traversable(($context["files"] ?? null));
            foreach ($context['_seq'] as $context["_key"] => $context["file"]) {
                // line 13
                echo "  .add('";
                echo PhpMyAdmin\Sanitize::escapeJsString(twig_get_attribute($this->env, $this->source, $context["file"], "filename", [], "any", false, false, false, 13));
                echo "', ";
                echo ((twig_get_attribute($this->env, $this->source, $context["file"], "has_onload", [], "any", false, false, false, 13)) ? (1) : (0));
                echo ")
";
            }
            $_parent = $context['_parent'];
            unset($context['_seq'], $context['_iterated'], $context['_key'], $context['file'], $context['_parent'], $context['loop']);
            $context = array_intersect_key($context, $_parent) + $_parent;
            // line 15
            echo ";
\$(function() {
";
            // line 17
            $context['_parent'] = $context;
            $context['_seq'] = twig_ensure_traversable(($context["files"] ?? null));
            foreach ($context['_seq'] as $context["_key"] => $context["file"]) {
                // line 18
                echo "  ";
                if (twig_get_attribute($this->env, $this->source, $context["file"], "has_onload", [], "any", false, false, false, 18)) {
                    // line 19
                    echo "  AJAX.fireOnload('";
                    echo PhpMyAdmin\Sanitize::escapeJsString(twig_get_attribute($this->env, $this->source, $context["file"], "filename", [], "any", false, false, false, 19));
                    echo "');
  ";
                }
            }
            $_parent = $context['_parent'];
            unset($context['_seq'], $context['_iterated'], $context['_key'], $context['file'], $context['_parent'], $context['loop']);
            $context = array_intersect_key($context, $_parent) + $_parent;
            // line 22
            echo "});
";
        }
        // line 24
        echo "// ]]>
</script>
";
    }

    public function getTemplateName()
    {
        return "scripts.twig";
    }

    public function isTraitable()
    {
        return false;
    }

    public function getDebugInfo()
    {
        return array (  109 => 24,  105 => 22,  95 => 19,  92 => 18,  88 => 17,  84 => 15,  73 => 13,  69 => 12,  66 => 11,  64 => 10,  60 => 9,  55 => 6,  47 => 4,  45 => 3,  41 => 2,  37 => 1,);
    }

    public function getSourceContext()
    {
        return new Source("", "scripts.twig", "/usr/local/CyberCP/public/phpmyadmin/templates/scripts.twig");
    }
}
