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

/* message.twig */
class __TwigTemplate_fea29803a44759292309da96e7a7d9ff2450076a4ae4563904d12d6d60cc4fc6 extends \Twig\Template
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
        echo "<div class=\"alert alert-";
        echo twig_escape_filter($this->env, ($context["context"] ?? null), "html", null, true);
        echo "\" role=\"alert\">
  ";
        // line 2
        echo ($context["message"] ?? null);
        echo "
</div>
";
    }

    public function getTemplateName()
    {
        return "message.twig";
    }

    public function isTraitable()
    {
        return false;
    }

    public function getDebugInfo()
    {
        return array (  42 => 2,  37 => 1,);
    }

    public function getSourceContext()
    {
        return new Source("", "message.twig", "/usr/local/CyberCP/public/phpmyadmin/templates/message.twig");
    }
}
