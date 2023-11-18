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

/* console/query_action.twig */
class __TwigTemplate_3ff12ee62b27a12d0e2dc5097f3a315e057e517d170d8eb01304a21924110695 extends \Twig\Template
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
        echo "<div class=\"";
        echo twig_escape_filter($this->env, ($context["parent_div_classes"] ?? null), "html", null, true);
        echo "\">
    ";
        // line 2
        $context['_parent'] = $context;
        $context['_seq'] = twig_ensure_traversable(($context["content_array"] ?? null));
        foreach ($context['_seq'] as $context["_key"] => $context["content"]) {
            // line 3
            echo "        ";
            if (array_key_exists("content", $context)) {
                // line 4
                echo "        <span class=\"";
                echo twig_escape_filter($this->env, (($__internal_compile_0 = $context["content"]) && is_array($__internal_compile_0) || $__internal_compile_0 instanceof ArrayAccess ? ($__internal_compile_0[0] ?? null) : null), "html", null, true);
                echo "\">
            ";
                // line 5
                echo twig_escape_filter($this->env, (($__internal_compile_1 = $context["content"]) && is_array($__internal_compile_1) || $__internal_compile_1 instanceof ArrayAccess ? ($__internal_compile_1[1] ?? null) : null), "html", null, true);
                echo "
            ";
                // line 6
                if (twig_get_attribute($this->env, $this->source, $context["content"], "extraSpan", [], "array", true, true, false, 6)) {
                    // line 7
                    echo "                : <span>";
                    echo twig_escape_filter($this->env, (($__internal_compile_2 = $context["content"]) && is_array($__internal_compile_2) || $__internal_compile_2 instanceof ArrayAccess ? ($__internal_compile_2["extraSpan"] ?? null) : null), "html", null, true);
                    echo "</span>
            ";
                }
                // line 9
                echo "        </span>
        ";
            }
            // line 11
            echo "    ";
        }
        $_parent = $context['_parent'];
        unset($context['_seq'], $context['_iterated'], $context['_key'], $context['content'], $context['_parent'], $context['loop']);
        $context = array_intersect_key($context, $_parent) + $_parent;
        // line 12
        echo "</div>
";
    }

    public function getTemplateName()
    {
        return "console/query_action.twig";
    }

    public function isTraitable()
    {
        return false;
    }

    public function getDebugInfo()
    {
        return array (  76 => 12,  70 => 11,  66 => 9,  60 => 7,  58 => 6,  54 => 5,  49 => 4,  46 => 3,  42 => 2,  37 => 1,);
    }

    public function getSourceContext()
    {
        return new Source("", "console/query_action.twig", "/usr/local/CyberCP/public/phpmyadmin/templates/console/query_action.twig");
    }
}
