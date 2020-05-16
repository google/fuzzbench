---
layout: default
title: Fuzzers
nav_order: 4
permalink: /reference/fuzzers/
parent: Reference
---

# Fuzzers

<table>
  <thead>
    <tr>
      <th style="text-align: center">Year</th>
      <th style="text-align: center">Name</th>
      <th style="text-align: center">Links</th>
      <th style="text-align: center">Description</th>
      <th style="text-align: center">Integration Status</th>
    </tr>
  </thead>
  <tbody>
    {% for fuzzer in site.data.fuzzers.Fuzzers %}
    <tr>
      <td style="text-align: center">{{ fuzzer.year }}</td>
      <td style="text-align: center">
        <a href="{{ fuzzer.url }}"> {{ fuzzer.name }}</a>
      </td>
      <td>
        <a href="https://www.google.com/search?q={{ fuzzer.name }}">
          <i class="fa fa-google"></i>
        </a>
        {% if fuzzer.url %}
        <a href="{{ fuzzer.url }}">
          <i class="fa fa-globe"></i>
        </a>
        {% endif %}
        {% if fuzzer.repo %}
        <a href="{{ fuzzer.repo }}">
          <i class='fa fa-code-branch'></i>
        </a>
        {% endif %}
        {% if fuzzer.dbpl %}
        <a href="https://dblp.org/rec/{{ fuzzer.dbpl }}">
          <i class='fa fa-graduation-cap'></i>
        </a>
        {% endif %}
      </td>
      <td>{{ fuzzer.desc }}</td>
      <td style="text-align: center">
        {% if fuzzer.integrated %}<i class="fa fa-check"></i>{% endif %}
        {% if fuzzer.issue %}
        <a href="{{ fuzzer.issue }}">
          <i class='fa fa-github'></i>
        </a>
        {% endif %}
      </td>
    </tr>
    {% endfor %}
  </tbody>
</table>

