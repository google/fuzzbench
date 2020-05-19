---
layout: default
title: Fuzzers
nav_order: 4
permalink: /reference/fuzzers/
parent: Reference
---

# Fuzzers

{% capture table_header %}
  <thead>
    <tr>
      <th style="text-align: center">Year</th>
      <th style="text-align: center">Name</th>
      <th style="text-align: center">Links</th>
      <th style="text-align: center">Description</th>
      <th style="text-align: center">Integration Status</th>
    </tr>
  </thead>
{% endcapture %}

## Already integrated

<table>
  {{ table_header }}
  <tbody>
    {% for fuzzer in site.data.fuzzers.Fuzzers %}
    {% if fuzzer.dir and fuzzer.experimental != true %}
    {% include_relative fuzzer_row.html %}
    {% endif %}
    {% endfor %}
  </tbody>
</table>

## Experimental integrations

<table>
  {{ table_header }}
  <tbody>
    {% for fuzzer in site.data.fuzzers.Fuzzers %}
    {% if fuzzer.dir and fuzzer.experimental == true %}
    {% include_relative fuzzer_row.html %}
    {% endif %}
    {% endfor %}
  </tbody>
</table>

## Would love to have

<table>
  {{ table_header }}
  <tbody>
    {% for fuzzer in site.data.fuzzers.Fuzzers %}
    {% unless fuzzer.dir %}
    {% include_relative fuzzer_row.html %}
    {% endunless %}
    {% endfor %}
  </tbody>
</table>
