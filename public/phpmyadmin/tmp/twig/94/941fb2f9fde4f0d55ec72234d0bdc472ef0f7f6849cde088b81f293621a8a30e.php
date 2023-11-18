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

/* console/toolbar.twig */
class __TwigTemplate_814aad6c4f931298b647951b2c3135da89afec63b41db4cf999f00f1ef56cbcd extends \Twig\Template
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
        echo "<div class=\"toolbar ";
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
                echo "        <div class=\"";
                echo twig_escape_filter($this->env, (($__internal_compile_0 = $context["content"]) && is_array($__internal_compile_0) || $__internal_compile_0 instanceof ArrayAccess ? ($__internal_compile_0[0] ?? null) : null), "html", null, true);
                echo "\">
            ";
                // line 5
                echo ((twig_get_attribute($this->env, $this->source, $context["content"], "image", [], "array", true, true, false, 5)) ? ((($__internal_compile_1 = $context["content"]) && is_array($__internal_compile_1) || $__internal_compile_1 instanceof ArrayAccess ? ($__internal_compile_1["image"] ?? null) : null)) : (""));
                echo "
            <span>";
                // line 6
                echo twig_escape_filter($this->env, (($__internal_compile_2 = $context["content"]) && is_array($__internal_compile_2) || $__internal_compile_2 instanceof ArrayAccess ? ($__internal_compile_2[1] ?? null) : null), "html", null, true);
                echo "</span>
        </div>
        ";
            }
            // line 9
            echo "    ";
        }
        $_parent = $context['_parent'];
        unset($context['_seq'], $context['_iterated'], $context['_key'], $context['content'], $context['_parent'], $context['loop']);
        $context = array_intersect_key($context, $_parent) + $_parent;
        // line 10
        echo "</div>
";
    }

    public function getTemplateName()
    {
        return "console/toolbar.twig";
    }

    public function isTraitable()
    {
        return false;
    }

    public function getDebugInfo()
    {
        return array (  70 => 10,  64 => 9,  58 => 6,  54 => 5,  49 => 4,  46 => 3,  42 => 2,  37 => 1,);
    }

    public function getSourceContext()
    {
        return new Source("", "console/toolbar.twig", "/usr/local/CyberCP/public/phpmyadmin/templates/console/toolbar.twig");
    }
}
