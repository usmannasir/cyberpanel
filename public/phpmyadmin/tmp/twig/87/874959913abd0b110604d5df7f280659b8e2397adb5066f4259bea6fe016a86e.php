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

/* select_lang.twig */
class __TwigTemplate_1bbe20e0e859a4b4d2f1e8510e6668a3c65faf7691521c7d218e589c74f66d48 extends \Twig\Template
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
        echo "    <form method=\"get\" action=\"";
        echo PhpMyAdmin\Url::getFromRoute("/");
        echo "\" class=\"disableAjax\">
    ";
        // line 2
        echo PhpMyAdmin\Url::getHiddenInputs(($context["_form_params"] ?? null));
        echo "

    ";
        // line 4
        if (($context["use_fieldset"] ?? null)) {
            // line 5
            echo "        <fieldset>
            <legend class=\"col-form-label\" lang=\"en\" dir=\"ltr\">";
            // line 6
            echo ($context["language_title"] ?? null);
            echo "</legend>
    ";
        } else {
            // line 8
            echo "        <bdo lang=\"en\" dir=\"ltr\">
            <label for=\"sel-lang\">";
            // line 9
            echo ($context["language_title"] ?? null);
            echo "</label>
        </bdo>
    ";
        }
        // line 12
        echo "
    <select name=\"lang\" class=\"autosubmit\" lang=\"en\" dir=\"ltr\" id=\"sel-lang\">

    ";
        // line 15
        $context['_parent'] = $context;
        $context['_seq'] = twig_ensure_traversable(($context["available_languages"] ?? null));
        foreach ($context['_seq'] as $context["_key"] => $context["language"]) {
            // line 16
            echo "        ";
            // line 17
            echo "        <option value=\"";
            echo twig_escape_filter($this->env, twig_lower_filter($this->env, twig_get_attribute($this->env, $this->source, $context["language"], "getCode", [], "method", false, false, false, 17)), "html", null, true);
            echo "\"";
            // line 18
            if (twig_get_attribute($this->env, $this->source, $context["language"], "isActive", [], "method", false, false, false, 18)) {
                // line 19
                echo "                selected=\"selected\"";
            }
            // line 21
            echo ">
        ";
            // line 22
            echo twig_get_attribute($this->env, $this->source, $context["language"], "getName", [], "method", false, false, false, 22);
            echo "
        </option>
    ";
        }
        $_parent = $context['_parent'];
        unset($context['_seq'], $context['_iterated'], $context['_key'], $context['language'], $context['_parent'], $context['loop']);
        $context = array_intersect_key($context, $_parent) + $_parent;
        // line 25
        echo "
    </select>

    ";
        // line 28
        if (($context["use_fieldset"] ?? null)) {
            // line 29
            echo "        </fieldset>
    ";
        }
        // line 31
        echo "
    </form>
";
    }

    public function getTemplateName()
    {
        return "select_lang.twig";
    }

    public function isTraitable()
    {
        return false;
    }

    public function getDebugInfo()
    {
        return array (  109 => 31,  105 => 29,  103 => 28,  98 => 25,  89 => 22,  86 => 21,  83 => 19,  81 => 18,  77 => 17,  75 => 16,  71 => 15,  66 => 12,  60 => 9,  57 => 8,  52 => 6,  49 => 5,  47 => 4,  42 => 2,  37 => 1,);
    }

    public function getSourceContext()
    {
        return new Source("", "select_lang.twig", "/usr/local/CyberCP/public/phpmyadmin/templates/select_lang.twig");
    }
}
